BEGIN;
UPDATE contracting_organisations SET commission_type = 'PERCENTAGE_OF_LUMP_SUM' WHERE commission_type = 'PERCENTAGE';
UPDATE contracting_organisations SET commission_type = 'FIXED_AMOUNT_PER_COLLECTION' WHERE commission_type = 'FIXED_PER_COLLECTION';
COMMIT;
