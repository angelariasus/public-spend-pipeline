#!/bin/bash
# Runs once, on the first start of an empty data volume (run it by hand on an
# existing one, see README). Creates:
#   - the read-only role BI tools use to query the warehouse marts; dbt grants
#     it SELECT on every mart it builds;
#   - Metabase's own application database.
set -euo pipefail

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  -v bi_user="$BI_READER_USER" \
  -v bi_password="$BI_READER_PASSWORD" \
  -v mb_user="$METABASE_DB_USER" \
  -v mb_password="$METABASE_DB_PASSWORD" \
  -v mb_db="$METABASE_DB" <<-'EOSQL'
	CREATE ROLE :"bi_user" LOGIN PASSWORD :'bi_password';
	CREATE ROLE :"mb_user" LOGIN PASSWORD :'mb_password';
	CREATE DATABASE :"mb_db" OWNER :"mb_user";
EOSQL
