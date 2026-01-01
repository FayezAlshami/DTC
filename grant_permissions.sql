-- SQL script to grant necessary permissions to user
-- Run this as PostgreSQL superuser (postgres)

-- Grant usage on schema public
GRANT USAGE ON SCHEMA public TO fayez;

-- Grant create privileges on schema public
GRANT CREATE ON SCHEMA public TO fayez;

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE dtc TO fayez;

-- Grant all privileges on all tables in public schema
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fayez;

-- Grant all privileges on all sequences in public schema
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fayez;

-- Grant privileges on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO fayez;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO fayez;

-- Make user owner of schema (alternative - more powerful)
-- ALTER SCHEMA public OWNER TO fayez;

