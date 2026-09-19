FROM postgres:16-alpine
COPY sql /project/sql
COPY deploy/postgres/01_init.sql /docker-entrypoint-initdb.d/01_init.sql
