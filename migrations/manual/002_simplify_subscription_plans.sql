-- Align an existing subscription_plans table with the simplified API model.
-- Existing billing cycle, price, and description values are preserved.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'subscription_plans' AND column_name = 'billing_cycle'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'subscription_plans' AND column_name = 'duration'
    ) THEN
        ALTER TABLE subscription_plans RENAME COLUMN billing_cycle TO duration;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'subscription_plans' AND column_name = 'price'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'subscription_plans' AND column_name = 'amount'
    ) THEN
        ALTER TABLE subscription_plans RENAME COLUMN price TO amount;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'subscription_plans' AND column_name = 'description'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'subscription_plans' AND column_name = 'notes'
    ) THEN
        ALTER TABLE subscription_plans RENAME COLUMN description TO notes;
    END IF;
END $$;

ALTER TABLE subscription_plans
    DROP COLUMN IF EXISTS name,
    DROP COLUMN IF EXISTS collections,
    DROP COLUMN IF EXISTS badge,
    DROP COLUMN IF EXISTS featured;
