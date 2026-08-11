ALTER TABLE customer
    ADD COLUMN IF NOT EXISTS number_of_bags INTEGER;

UPDATE customer
SET number_of_bags = 0
WHERE number_of_bags IS NULL;

ALTER TABLE customer
    ALTER COLUMN number_of_bags SET DEFAULT 0,
    ALTER COLUMN number_of_bags SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_customer_number_of_bags_nonnegative'
          AND conrelid = 'customer'::regclass
    ) THEN
        ALTER TABLE customer
            ADD CONSTRAINT ck_customer_number_of_bags_nonnegative
            CHECK (number_of_bags >= 0);
    END IF;
END $$;
