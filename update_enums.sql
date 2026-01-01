-- SQL script to update enum types in PostgreSQL
-- Run this script in your PostgreSQL database (using psql or pgAdmin)

-- Add new values to servicestatus enum
ALTER TYPE servicestatus ADD VALUE IF NOT EXISTS 'pending';
ALTER TYPE servicestatus ADD VALUE IF NOT EXISTS 'rejected';

-- Add new values to requeststatus enum  
ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'pending';
ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'rejected';

-- Verify the changes
SELECT unnest(enum_range(NULL::servicestatus))::text AS servicestatus_values;
SELECT unnest(enum_range(NULL::requeststatus))::text AS requeststatus_values;

