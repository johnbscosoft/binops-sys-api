BEGIN;

CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    property_code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    property_type VARCHAR(20) NOT NULL,
    billing_mode VARCHAR(20) NOT NULL,
    owner_customer_id INTEGER REFERENCES customer(id),
    subscription_plan_id UUID REFERENCES subscription_plans(id),
    location VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'Active',
    legacy_customer_id INTEGER UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_properties_company_name UNIQUE (company_id, name),
    CONSTRAINT ck_properties_type CHECK (property_type IN ('APARTMENT', 'RENTAL')),
    CONSTRAINT ck_properties_billing_mode CHECK (billing_mode IN ('OWNER', 'TENANT')),
    CONSTRAINT ck_properties_status CHECK (status IN ('Active', 'Inactive'))
);

CREATE INDEX IF NOT EXISTS ix_properties_company_id ON properties(company_id);
CREATE INDEX IF NOT EXISTS ix_properties_property_code ON properties(property_code);
CREATE INDEX IF NOT EXISTS ix_properties_owner_customer_id ON properties(owner_customer_id);
CREATE INDEX IF NOT EXISTS ix_properties_subscription_plan_id ON properties(subscription_plan_id);

CREATE TABLE IF NOT EXISTS property_units (
    id UUID PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    room_number VARCHAR(80) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_property_units_room UNIQUE (property_id, room_number)
);

CREATE INDEX IF NOT EXISTS ix_property_units_property_id ON property_units(property_id);
CREATE INDEX IF NOT EXISTS ix_property_units_company_id ON property_units(company_id);

CREATE TABLE IF NOT EXISTS property_occupancies (
    id UUID PRIMARY KEY,
    property_unit_id UUID NOT NULL REFERENCES property_units(id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES customer(id),
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_property_occupancies_date_order
        CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS ix_property_occupancies_unit_id
    ON property_occupancies(property_unit_id);
CREATE INDEX IF NOT EXISTS ix_property_occupancies_customer_id
    ON property_occupancies(customer_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_property_occupancies_current_unit
    ON property_occupancies(property_unit_id) WHERE is_current = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_property_occupancies_current_customer
    ON property_occupancies(customer_id) WHERE is_current = TRUE;

-- Convert properties created through the earlier embedded-room design.
INSERT INTO properties (
    id,
    company_id,
    property_code,
    name,
    property_type,
    billing_mode,
    owner_customer_id,
    subscription_plan_id,
    location,
    status,
    legacy_customer_id,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    customer.company_id,
    'PROP-' || UPPER(SUBSTRING(MD5(customer.id::TEXT), 1, 8)),
    customer.name,
    CASE WHEN LOWER(category.name) = 'rentals' THEN 'RENTAL' ELSE 'APARTMENT' END,
    CASE WHEN customer.service_arrangement = 'LANDLORD' THEN 'OWNER' ELSE 'TENANT' END,
    CASE WHEN customer.service_arrangement = 'LANDLORD' THEN customer.id ELSE NULL END,
    CASE WHEN customer.service_arrangement = 'LANDLORD' THEN customer.subscription_plan_id ELSE NULL END,
    customer.location,
    customer.status,
    customer.id,
    customer.date_entered,
    customer.date_updated
FROM customer
JOIN client_categories AS category ON category.id = customer.client_category_id
WHERE customer.customer_type = 'PROPERTY'
  AND NOT EXISTS (
      SELECT 1 FROM properties WHERE properties.legacy_customer_id = customer.id
  );

INSERT INTO property_units (
    id,
    property_id,
    company_id,
    room_number,
    is_active,
    created_at,
    updated_at
)
SELECT
    room.id,
    property.id,
    room.company_id,
    room.room_number,
    TRUE,
    room.created_at,
    room.updated_at
FROM customer_rooms AS room
JOIN properties AS property ON property.legacy_customer_id = room.customer_id
ON CONFLICT (id) DO NOTHING;

INSERT INTO property_occupancies (
    id,
    property_unit_id,
    customer_id,
    start_date,
    end_date,
    is_current,
    created_at,
    updated_at
)
SELECT
    occupancy.id,
    occupancy.room_id,
    occupancy.occupant_customer_id,
    occupancy.start_date,
    occupancy.end_date,
    occupancy.is_current,
    occupancy.created_at,
    occupancy.updated_at
FROM room_occupancies AS occupancy
JOIN property_units AS unit ON unit.id = occupancy.room_id
ON CONFLICT (id) DO NOTHING;

-- Tenant customers inherit Apartment/Rentals from the property they occupy.
UPDATE customer AS occupant
SET client_category_id = matching_category.id,
    customer_type = 'STANDARD'
FROM property_occupancies AS occupancy
JOIN property_units AS unit ON unit.id = occupancy.property_unit_id
JOIN properties AS property ON property.id = unit.property_id
JOIN client_categories AS matching_category
  ON matching_category.company_id = property.company_id
 AND LOWER(matching_category.name) = CASE
     WHEN property.property_type = 'APARTMENT' THEN 'apartment'
     ELSE 'rentals'
 END
WHERE occupant.id = occupancy.customer_id;

-- A legacy property account becomes the owner/customer contact; the physical
-- property is now represented only in the properties table.
UPDATE customer AS owner
SET client_category_id = individual_category.id,
    customer_type = 'STANDARD',
    service_arrangement = NULL,
    room_pricing_mode = NULL,
    caretaker_name = NULL,
    caretaker_phone = NULL
FROM properties AS property
JOIN client_categories AS individual_category
  ON individual_category.company_id = property.company_id
 AND LOWER(individual_category.name) = 'individual'
WHERE property.legacy_customer_id = owner.id;

COMMIT;
