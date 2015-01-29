gosu postgres postgres --single <<- EOSQL
  CREATE USER lightning WITH PASSWORD 'mypassword' CREATEDB;
  CREATE DATABASE lightning;
  GRANT ALL PRIVILEGES ON DATABASE lightning TO lightning;
EOSQL
