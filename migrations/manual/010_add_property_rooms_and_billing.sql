BEGIN;

ALTER TABLE customer
    ADD COLUMN IF NOT EXISTS service_arrangement VARCHAR(30),
    ADD COLUMN IF NOT EXISTS room_pricing_mode VARCHAR(20),
    ADD COLUMN IF NOT EXISTS caretaker_name VARCHAR(160),
    ADD COLUMN IF NOT EXISTS caretaker_phone VARCHAR(40),
    ADD COLUMN IF NOT EXISTS customer_type VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
    ADD COLUMN IF NOT EXISTS agreed_price NUMERIC(14, 2);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_customer_service_arrangement') THEN
        ALTER TABLE customer ADD CONSTRAINT ck_customer_service_arrangement
            CHECK (service_arrangement IS NULL OR service_arrangement IN ('LANDLORD', 'DIRECT_TENANT'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_customer_room_pricing_mode') THEN
        ALTER TABLE customer ADD CONSTRAINT ck_customer_room_pricing_mode
            CHECK (room_pricing_mode IS NULL OR room_pricing_mode IN ('SHARED', 'PER_ROOM'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_customer_customer_type') THEN
        ALTER TABLE customer ADD CONSTRAINT ck_customer_customer_type
            CHECK (customer_type IN ('STANDARD', 'PROPERTY', 'OCCUPANT'));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS customer_rooms (
    id UUID PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customer(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    room_number VARCHAR(80) NOT NULL,
    occupancy_status VARCHAR(20) NOT NULL DEFAULT 'Vacant',
    occupant_name VARCHAR(160),
    phone_number VARCHAR(40),
    email VARCHAR(255),
    subscription_plan_id UUID REFERENCES subscription_plans(id),
    price NUMERIC(14, 2),
    number_of_bags INTEGER NOT NULL DEFAULT 0,
    uses_default_pricing BOOLEAN NOT NULL DEFAULT TRUE,
    account_status VARCHAR(20) NOT NULL DEFAULT 'Active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_customer_rooms_customer_room UNIQUE (customer_id, room_number),
    CONSTRAINT ck_customer_rooms_bags_nonnegative CHECK (number_of_bags >= 0),
    CONSTRAINT ck_customer_rooms_occupancy_status CHECK (occupancy_status IN ('Occupied', 'Vacant')),
    CONSTRAINT ck_customer_rooms_account_status CHECK (account_status IN ('Active', 'Inactive'))
);

CREATE INDEX IF NOT EXISTS ix_customer_rooms_customer_id ON customer_rooms(customer_id);
CREATE INDEX IF NOT EXISTS ix_customer_rooms_company_id ON customer_rooms(company_id);
CREATE INDEX IF NOT EXISTS ix_customer_rooms_subscription_plan_id ON customer_rooms(subscription_plan_id);

CREATE TABLE IF NOT EXISTS room_occupancies (
    id UUID PRIMARY KEY,
    room_id UUID NOT NULL REFERENCES customer_rooms(id) ON DELETE CASCADE,
    occupant_customer_id INTEGER NOT NULL REFERENCES customer(id),
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_room_occupancies_date_order CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS ix_room_occupancies_room_id ON room_occupancies(room_id);
CREATE INDEX IF NOT EXISTS ix_room_occupancies_occupant_customer_id
    ON room_occupancies(occupant_customer_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_room_occupancies_current_room
    ON room_occupancies(room_id)
    WHERE is_current = TRUE;

UPDATE customer
SET customer_type = 'PROPERTY'
FROM client_categories
WHERE customer.client_category_id = client_categories.id
  AND LOWER(client_categories.name) IN ('apartment', 'rentals')
  AND customer.customer_type = 'STANDARD';

COMMIT;
