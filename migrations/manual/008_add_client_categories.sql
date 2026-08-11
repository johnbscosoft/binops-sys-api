CREATE TABLE IF NOT EXISTS client_categories (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_client_categories_company_name UNIQUE (company_id, name)
);

CREATE INDEX IF NOT EXISTS ix_client_categories_company_id
    ON client_categories(company_id);

INSERT INTO client_categories (id, company_id, name, is_active)
SELECT gen_random_uuid(), companies.id, defaults.name, TRUE
FROM companies
CROSS JOIN (
    VALUES
        ('Individual'),
        ('Apartment'),
        ('Shopping Mall'),
        ('School'),
        ('University'),
        ('Rentals')
) AS defaults(name)
WHERE NOT EXISTS (
    SELECT 1
    FROM client_categories
    WHERE client_categories.company_id = companies.id
      AND LOWER(client_categories.name) = LOWER(defaults.name)
)
ON CONFLICT (company_id, name) DO NOTHING;

ALTER TABLE customer
    ADD COLUMN IF NOT EXISTS client_category_id UUID;

UPDATE customer
SET client_category_id = client_categories.id
FROM client_categories
WHERE customer.company_id = client_categories.company_id
  AND client_categories.name = 'Individual'
  AND customer.client_category_id IS NULL;

ALTER TABLE customer
    ALTER COLUMN client_category_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_customer_client_category_id'
          AND conrelid = 'customer'::regclass
    ) THEN
        ALTER TABLE customer
            ADD CONSTRAINT fk_customer_client_category_id
            FOREIGN KEY (client_category_id)
            REFERENCES client_categories(id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_customer_client_category_id
    ON customer(client_category_id);
