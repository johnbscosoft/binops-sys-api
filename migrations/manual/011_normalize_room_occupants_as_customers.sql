BEGIN;

ALTER TABLE customer
    ADD COLUMN IF NOT EXISTS customer_type VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
    ADD COLUMN IF NOT EXISTS agreed_price NUMERIC(14, 2);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_customer_customer_type') THEN
        ALTER TABLE customer ADD CONSTRAINT ck_customer_customer_type
            CHECK (customer_type IN ('STANDARD', 'PROPERTY', 'OCCUPANT'));
    END IF;
END $$;

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

DO $$
DECLARE
    room_record RECORD;
    individual_category_id UUID;
    occupant_id INTEGER;
BEGIN
    FOR room_record IN
        SELECT
            room.*,
            property.location AS property_location,
            property.latitude AS property_latitude,
            property.longitude AS property_longitude,
            property.place_id AS property_place_id,
            property.house_no AS property_house_no,
            property.subscription_plan_id AS property_plan_id,
            property.service_arrangement AS property_arrangement
        FROM customer_rooms AS room
        JOIN customer AS property ON property.id = room.customer_id
        WHERE room.occupancy_status = 'Occupied'
          AND room.occupant_name IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM room_occupancies AS occupancy
              WHERE occupancy.room_id = room.id AND occupancy.is_current = TRUE
          )
    LOOP
        SELECT id INTO individual_category_id
        FROM client_categories
        WHERE company_id = room_record.company_id
          AND LOWER(name) = 'individual'
        LIMIT 1;

        IF individual_category_id IS NULL THEN
            RAISE EXCEPTION 'Individual client category is missing for company %', room_record.company_id;
        END IF;

        INSERT INTO customer (
            company_id,
            name,
            phone_no,
            email,
            location,
            latitude,
            longitude,
            place_id,
            flat_no,
            house_no,
            number_of_bags,
            client_category_id,
            subscription_plan_id,
            agreed_price,
            customer_type,
            status
        ) VALUES (
            room_record.company_id,
            room_record.occupant_name,
            room_record.phone_number,
            room_record.email,
            room_record.property_location,
            room_record.property_latitude,
            room_record.property_longitude,
            room_record.property_place_id,
            room_record.room_number,
            room_record.property_house_no,
            room_record.number_of_bags,
            individual_category_id,
            CASE
                WHEN room_record.property_arrangement = 'DIRECT_TENANT'
                    THEN COALESCE(room_record.subscription_plan_id, room_record.property_plan_id)
                ELSE NULL
            END,
            CASE
                WHEN room_record.property_arrangement = 'DIRECT_TENANT' THEN room_record.price
                ELSE NULL
            END,
            'OCCUPANT',
            room_record.account_status
        ) RETURNING id INTO occupant_id;

        INSERT INTO room_occupancies (id, room_id, occupant_customer_id)
        VALUES (gen_random_uuid(), room_record.id, occupant_id);
    END LOOP;
END $$;

COMMIT;
