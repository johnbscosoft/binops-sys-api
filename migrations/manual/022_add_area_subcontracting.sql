BEGIN;
CREATE TABLE IF NOT EXISTS contracting_organisations (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE, name VARCHAR(200) NOT NULL, commission_type VARCHAR(30) NOT NULL, commission_rate NUMERIC(14,2) NOT NULL, contract_start_date DATE, contract_end_date DATE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), CONSTRAINT uq_contracting_organisations_company_name UNIQUE(company_id, name));
ALTER TABLE collection_areas ADD COLUMN IF NOT EXISTS service_model VARCHAR(20) NOT NULL DEFAULT 'DIRECT', ADD COLUMN IF NOT EXISTS contracting_organisation_id UUID REFERENCES contracting_organisations(id);
COMMIT;
