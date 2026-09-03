BEGIN;

ALTER TABLE authentication_settings
    ADD COLUMN IF NOT EXISTS google_location_enabled BOOLEAN NOT NULL DEFAULT FALSE;

COMMIT;
