CREATE TABLE IF NOT EXISTS authentication_settings (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
    otp_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    email_otp_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sms_otp_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_authentication_settings_company_id
    ON authentication_settings(company_id);
