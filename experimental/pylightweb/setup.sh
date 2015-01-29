apt-get install -y python-psycopg2

gosu postgres postgres --single <<- EOSQL
  CREATE USER lightning WITH PASSWORD 'mypassword' CREATEDB;
  CREATE DATABASE lightning;
  GRANT ALL PRIVILEGES ON DATABASE lightning TO lightning;
EOSQL

cd /home/lightning/lightning/experimental/pylightweb/lightning
git pull
