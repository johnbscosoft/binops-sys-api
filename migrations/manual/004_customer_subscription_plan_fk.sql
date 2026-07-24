-- Replace duplicated subscription text/amount with a plan foreign key.
ALTER TABLE customer
    ADD COLUMN IF NOT EXISTS subscription_plan_id UUID;

-- Preserve existing links where duration, frequency, amount, and company match.
UPDATE customer AS customer_record
SET subscription_plan_id = (
    SELECT plan.id
    FROM subscription_plans AS plan
    WHERE plan.company_id = customer_record.company_id
      AND plan.amount = customer_record.contract_amount
      AND lower(customer_record.subscription_type) LIKE '%' || lower(plan.duration) || '%'
      AND lower(customer_record.subscription_type) LIKE '%' || lower(plan.pickup_frequency) || '%'
    ORDER BY plan.created_at
    LIMIT 1
)
WHERE customer_record.subscription_plan_id IS NULL
  AND EXISTS (
    SELECT 1
    FROM subscription_plans AS plan
    WHERE plan.company_id = customer_record.company_id
      AND plan.amount = customer_record.contract_amount
      AND lower(customer_record.subscription_type) LIKE '%' || lower(plan.duration) || '%'
      AND lower(customer_record.subscription_type) LIKE '%' || lower(plan.pickup_frequency) || '%'
  );

ALTER TABLE customer
    DROP COLUMN IF EXISTS subscription_type,
    DROP COLUMN IF EXISTS contract_amount;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_customer_subscription_plan_id'
    ) THEN
        ALTER TABLE customer
            ADD CONSTRAINT fk_customer_subscription_plan_id
            FOREIGN KEY (subscription_plan_id)
            REFERENCES subscription_plans(id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_customer_subscription_plan_id
    ON customer (subscription_plan_id);
