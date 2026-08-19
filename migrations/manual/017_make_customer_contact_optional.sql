BEGIN;

-- Phone number and email are optional for customers. Existing values are retained.
ALTER TABLE customer ALTER COLUMN phone_no DROP NOT NULL;
ALTER TABLE customer ALTER COLUMN email DROP NOT NULL;

COMMIT;
