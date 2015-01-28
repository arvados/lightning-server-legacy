README

apt-get update
apt-get install build-essential
apt-get install git
apt-get install python-pip

For golang and lantern:
  apt-get install wget

For cgzip:
  apt-get install mercurial
  apt-get install pkg-config
  create file: /usr/lib/pkgconfig/zlib.pc
    prefix=/usr
    exec_prefix=${prefix}
    libdir=${exec_prefix}/lib
    sharedlibdir=${libdir}
    includedir=${prefix}/include

    Name: zlib
    Description: zlib compression library
    Version: 1.2.5

    Requires:
    Libs: -L${libdir} -L${sharedlibdir} -lz
    Cflags: -I${includedir}

  apt-get install alien
  wget ftp://rpmfind.net/linux/sourceforge/r/ra/ramonelinux/Rel_0.99/releases/x86_64/packages/zlib-1.2.8-2.ram0.99.x86_64.rpm
  alien -i zlib-1.2.8-2.ram0.99.x86_64.rpm

adduser lightning
password: mypassword
name: Lightning Server Application

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

(I believe the addition of sources broke the build-essential package)
cat > /etc/apt/sources.list  
deb http://archive.ubuntu.com/ubuntu precise main universe multiverse

apt-get install python
apt-get install python-pip
pip install django



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
