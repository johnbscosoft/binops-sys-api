BEGIN;

CREATE TABLE IF NOT EXISTS collection_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    area_code VARCHAR(40) NOT NULL,
    name VARCHAR(160) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_collection_areas_company_code UNIQUE (company_id, area_code),
    CONSTRAINT uq_collection_areas_company_id_code UNIQUE (company_id, id, area_code)
);

CREATE TABLE IF NOT EXISTS collection_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    area_id UUID NOT NULL,
    area_code VARCHAR(40) NOT NULL,
    name VARCHAR(160) NOT NULL,
    vehicle_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_collection_routes_company_name UNIQUE (company_id, name),
    CONSTRAINT fk_collection_routes_company_area_code
        FOREIGN KEY (company_id, area_id, area_code)
        REFERENCES collection_areas(company_id, id, area_code)
);

CREATE INDEX IF NOT EXISTS ix_collection_areas_company_id ON collection_areas(company_id);
CREATE INDEX IF NOT EXISTS ix_collection_routes_company_id ON collection_routes(company_id);
CREATE INDEX IF NOT EXISTS ix_collection_routes_area_id ON collection_routes(area_id);

COMMIT;
