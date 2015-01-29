
FROM ubuntu:12.04
MAINTAINER sguthrie@curoverse.com

# Add the PostgreSQL PGP key to verify their Debian packages.
# It should be the same key as https://www.postgresql.org/media/keys/ACCC4CF8.asc
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8

# Add PostgreSQL's repository. It contains the most recent stable release
#     of PostgreSQL, ``9.3``.
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main" > /etc/apt/sources.list.d/pgdg.list

RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
  build-essential \
  curl \
  git \
  mercurial \
  pkg-config \
  postgresql-9.3 \
  postgresql-client-9.3 \
  postgresql-contrib-9.3 \
  python-pip \
  python-software-properties \
  software-properties-common \
  zlib1g-dev

RUN pip install django
RUN pip install django-bootstrap-form
RUN pip install djangorestframework

# Install go
RUN curl https://storage.googleapis.com/golang/go1.3.1.linux-amd64.tar.gz | tar -C /usr/local -zx
ENV GOROOT /usr/local/go
ENV PATH /usr/local/go/bin:$PATH

# Add lightning as a user, set up go environment
RUN useradd lightning
RUN mkdir /home/lightning && chown -R lightning: /home/lightning
RUN mkdir /home/lightning/go
ENV GOPATH /home/lightning/go:$GOPATH

WORKDIR /home/lightning
RUN git clone https://github.com/curoverse/lightning.git
WORKDIR /home/lightning/lightning/experimental/lantern
RUN go get github.com/codegangsta/cli
RUN go get code.google.com/p/vitess/go/cgzip
RUN go get github.com/lib/pq
RUN go get github.com/mattn/go-sqlite3
RUN go build

# Run the rest of the commands as the ``postgres`` user created by the ``postgres-9.3`` package when it was ``apt-get installed``
USER postgres

# Create a PostgreSQL role named ``docker`` with ``docker`` as the password and
# then create a database `docker` owned by the ``docker`` role.
# Note: here we use ``&&\`` to run commands one after the other - the ``\``
#       allows the RUN command to span multiple lines.
RUN    /etc/init.d/postgresql start &&\
    psql --command "CREATE USER lightning WITH CREATEDB PASSWORD 'mypassword';" &&\
    createdb -O lightning lightning

# Adjust PostgreSQL configuration so that remote connections to the
# database are possible.
RUN echo "host all  all    0.0.0.0/0  md5" >> /etc/postgresql/9.3/main/pg_hba.conf

# And add ``listen_addresses`` to ``/etc/postgresql/9.3/main/postgresql.conf``
RUN echo "listen_addresses='*'" >> /etc/postgresql/9.3/main/postgresql.conf

# Expose the PostgreSQL port
EXPOSE 5432

USER lightning

WORKDIR /home/lightning/lightning/experimental/pylightweb/lightning

RUN python manage.py migrate
RUN python manage.py test tile_library

# Set the default command to run when starting the container
#CMD ["/usr/lib/postgresql/9.3/bin/postgres", "-D", "/var/lib/postgresql/9.3/main", "-c", "config_file=/etc/postgresql/9.3/main/postgresql.conf"]
