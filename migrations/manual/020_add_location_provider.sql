BEGIN;

ALTER TABLE authentication_settings
    ADD COLUMN IF NOT EXISTS location_provider VARCHAR(20) NOT NULL DEFAULT 'MANUAL';

UPDATE authentication_settings
SET location_provider = 'GOOGLE'
WHERE google_location_enabled = TRUE;

COMMIT;
