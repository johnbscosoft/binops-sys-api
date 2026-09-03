BEGIN;

ALTER TABLE collection_routes ADD COLUMN IF NOT EXISTS route_code VARCHAR(40);
WITH numbered AS (SELECT id, area_code || '-R' || LPAD(ROW_NUMBER() OVER (PARTITION BY company_id, area_code ORDER BY created_at)::text, 2, '0') AS code FROM collection_routes WHERE route_code IS NULL) UPDATE collection_routes SET route_code = numbered.code FROM numbered WHERE collection_routes.id = numbered.id;
ALTER TABLE collection_routes ALTER COLUMN route_code SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_collection_routes_company_code ON collection_routes(company_id, route_code);

COMMIT;
