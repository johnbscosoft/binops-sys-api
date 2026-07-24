CREATE TABLE IF NOT EXISTS customer_contracts (
    id UUID PRIMARY KEY,
    contract_code VARCHAR(40) NOT NULL UNIQUE,
    company_id UUID NOT NULL REFERENCES companies(id),
    customer_id INTEGER NOT NULL REFERENCES customer(id),
    subscription_plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    customer_code VARCHAR(40) NOT NULL,
    customer_name VARCHAR NOT NULL,
    plan_duration VARCHAR(80) NOT NULL,
    pickup_frequency VARCHAR(80) NOT NULL,
    agreed_amount NUMERIC(14, 2) NOT NULL,
    start_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_customer_contracts_company_id ON customer_contracts(company_id);
CREATE INDEX IF NOT EXISTS ix_customer_contracts_customer_id ON customer_contracts(customer_id);
CREATE INDEX IF NOT EXISTS ix_customer_contracts_subscription_plan_id ON customer_contracts(subscription_plan_id);
CREATE INDEX IF NOT EXISTS ix_customer_contracts_expiry_date ON customer_contracts(expiry_date);
