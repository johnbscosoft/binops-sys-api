BEGIN;

UPDATE customer AS occupant
SET location = property.location,
    latitude = NULL,
    longitude = NULL,
    place_id = NULL
FROM property_occupancies AS occupancy
JOIN property_units AS unit ON unit.id = occupancy.property_unit_id
JOIN properties AS property ON property.id = unit.property_id
WHERE occupancy.customer_id = occupant.id
  AND occupancy.is_current = TRUE
  AND property.location IS NOT NULL;

UPDATE customer AS billing_customer
SET location = property.location,
    latitude = NULL,
    longitude = NULL,
    place_id = NULL
FROM properties AS property
WHERE property.owner_customer_id = billing_customer.id
  AND property.billing_mode = 'OWNER'
  AND property.location IS NOT NULL;

COMMIT;
