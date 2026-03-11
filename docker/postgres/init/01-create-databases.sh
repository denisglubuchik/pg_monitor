#!/bin/sh
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    CREATE DATABASE monitored_db;
    CREATE DATABASE pg_monitor_storage;
EOSQL
