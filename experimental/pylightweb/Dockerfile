#First time trying to setup a Dockerfile; taken from http://docs.docker.com/examples/postgresql_service/ since I don't understand the postgres docker image use

FROM postgres:9.3.5
MAINTAINER sguthrie@curoverse.com

RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  git \
  mercurial \
  pkg-config \
  python-pip \
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

WORKDIR /
COPY /home/lightning/lightning/experimental/pylightweb/setup.sh /docker-entrypoint-initdb.d/setup.sh
