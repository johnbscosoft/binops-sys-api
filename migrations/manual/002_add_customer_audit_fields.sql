-- Adds audit fields to the existing customer table.
--
-- Run with:
-- psql "postgresql://admin:admin123@localhost:5432/wasteops_db" -f migrations/manual/002_add_customer_audit_fields.sql

ALTER TABLE customer
    ADD COLUMN IF NOT EXISTS date_entered TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS added_by VARCHAR,
    ADD COLUMN IF NOT EXISTS updated_by VARCHAR;
