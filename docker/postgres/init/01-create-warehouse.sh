#!/bin/bash
# Runs once, on the first start of an empty data volume.
# Creates the analytics warehouse database next to the Airflow metadata DB.
set -euo pipefail

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  -v wh_user="$WAREHOUSE_USER" \
  -v wh_password="$WAREHOUSE_PASSWORD" \
  -v wh_db="$WAREHOUSE_DB" <<-'EOSQL'
	CREATE ROLE :"wh_user" LOGIN PASSWORD :'wh_password';
	CREATE DATABASE :"wh_db" OWNER :"wh_user";
EOSQL
