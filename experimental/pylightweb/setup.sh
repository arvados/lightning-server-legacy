apt-get install -y python-psycopg2

gosu postgres postgres --single <<- EOSQL
  CREATE USER lightning WITH PASSWORD 'mypassword' CREATEDB;
  CREATE DATABASE lightning;
  GRANT ALL PRIVILEGES ON DATABASE lightning TO lightning;
EOSQL

python /lightning/experimental/pylightweb/lightning/manage.py migrate
python /lightning/experimental/pylightweb/lightning/manage.py test tile_library
