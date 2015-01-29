README
Sequence to run in docker:

vi /usr/sbin/policy-rc.d
  #!/bin/sh
  exit 0

apt-get update
apt-get install build-essential
apt-get install git
apt-get install wget (for golang and lantern)
apt-get install mercurial (for cgzip)
apt-get install pkg-config (for cgzip)
apt-get install zlib1g-dev (for cgzip)
apt-get install python-pip (for django)
apt-get install postgresql-9.3 (for postgres)
apt-get install python-psycopg2 (for postgres+django)
pip install django
pip install django-bootstrap-form
pip install djangorestframework

adduser lightning
password: mypassword
name: Lightning Server Application

su postgres
  createuser -P -d lightning
    password: mypassword
  createdb lightning

/home/lightning/# mkdir golang
/home/lightning/golang# wget https://storage.googleapis.com/golang/go1.3.1.linux-amd64.tar.gz
/home/lightning/golang# tar -xzf go1.3.1.linux-amd64.tar.gz
(Add lines to /home/lighting/.bashrc:
  export GOROOT=/home/lightning/golang/go
  export GOPATH=/home/lightning/golang/
  export PATH=$PATH:$GOROOT/bin
  )
/home/lightning# source .bashrc
/home/lightning/# git clone https://github.com/curoverse/lightning.git
/home/lightning/lightning/experimental/lantern# go get github.com/codegangsta/cli
/home/lightning/lightning/experimental/lantern# go get code.google.com/p/vitess/go/cgzip
/home/lightning/lightning/experimental/lantern# go get github.com/lib/pq
/home/lightning/lightning/experimental/lantern# go get github.com/mattn/go-sqlite3
/home/lightning/lightning/experimental/lantern# go build

/home/lightning/lightning/experimental/pylightweb/lightning# python manage.py migrate
(/home/lightning/lightning/experimental/pylightweb/lightning# python manage.py test tile_library)



Folders
=======================

## api/
   Supported API - includes a view for documentation

## api_gui/
   Forms and custom visualization for API

## lightning/
  Provides django settings for website, server configuration, and home/help pages

## static/
  Contains js and css files used by the entire site

## templates/
  Contains the base html document to add bootstrap to all application webpages
  Contains all templates shown in website

## tile_library/
  Lightning models/database. Contains querying functions for postgres and lantern and
  functions designed for use with CGF.

=======================
## manage.py
  Runs django commands

## errors.py
  Implements lightning-wide errors

Known errors:
  generate_stats does not look at tags!
