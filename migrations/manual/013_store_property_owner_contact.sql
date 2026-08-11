BEGIN;

ALTER TABLE properties
    ADD COLUMN IF NOT EXISTS owner_name VARCHAR(160),
    ADD COLUMN IF NOT EXISTS owner_phone_number VARCHAR(40),
    ADD COLUMN IF NOT EXISTS owner_email VARCHAR(255);

UPDATE properties AS property
SET owner_name = COALESCE(property.owner_name, owner.name),
    owner_phone_number = COALESCE(property.owner_phone_number, owner.phone_no),
    owner_email = COALESCE(property.owner_email, owner.email)
FROM customer AS owner
WHERE property.owner_customer_id = owner.id;

UPDATE customer AS billing_customer
SET name = property.name
FROM properties AS property
WHERE property.owner_customer_id = billing_customer.id
  AND property.billing_mode = 'OWNER';

COMMIT;
