-- Runs once on a fresh volume (docker-entrypoint-initdb.d). Local development only.
-- Read-only role used by the `postgres` MCP server (.mcp.json). Never grant write access.
CREATE ROLE kame_apply_ro LOGIN PASSWORD 'kame_apply_ro_local_only' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
GRANT CONNECT ON DATABASE kame_apply TO kame_apply_ro;
\connect kame_apply
GRANT USAGE ON SCHEMA public TO kame_apply_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public GRANT SELECT ON TABLES TO kame_apply_ro;

-- Separate database for the test suite so tests can reset freely.
\connect postgres
CREATE DATABASE kame_apply_test OWNER kame_apply;
