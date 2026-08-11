BEGIN;

ALTER TABLE property_units
    ADD COLUMN IF NOT EXISTS occupancy_status VARCHAR(20) NOT NULL DEFAULT 'Vacant';

UPDATE property_units AS unit
SET occupancy_status = 'Occupied'
WHERE EXISTS (
    SELECT 1
    FROM property_occupancies AS occupancy
    WHERE occupancy.property_unit_id = unit.id
      AND occupancy.is_current = TRUE
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_property_units_occupancy_status'
          AND conrelid = 'property_units'::regclass
    ) THEN
        ALTER TABLE property_units
            ADD CONSTRAINT ck_property_units_occupancy_status
            CHECK (occupancy_status IN ('Occupied', 'Vacant'));
    END IF;
END $$;

COMMIT;
