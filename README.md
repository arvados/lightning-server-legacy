Lightning
=========

## Setting-up a local lightning cluster:
* This will **not** populate the database with a tile library or population. These capabilities are under development.
* An official Curoverse and/or Arvados docker image is in development.

## Recipe:
1.	Install docker (https://docs.docker.com/installation/)
2.	Start a container running postgres (named base-postgres here)
    ```
	$ docker run --name base-postgres -e POSTGRES_USER=lightning -e POSTGRES_PASSWORD=mypassword -d postgres
	```
3.	Download the lightning docker image (currently sguthrie/lightning)

	a. You can do this by pulling sguthrie/lightning from the docker repository
    ```
	$ docker pull sguthrie/lightning
    ```
	b. Or building it yourself using the Dockerfile in this git repository (which takes more time but guarantees the image is up-to-date)
    ```
 	lightning/experimental/pylightweb$ docker build -t sguthrie/lightning .
    ```
4.  Run an interactive lightning container and link it to the the postgres container
    ```
	$ docker run --name lightning -it --rm --link base-postgres:postgres sguthrie/lightning /bin/bash
    ```
5.	Inside the lightning container, in case the docker image is out of date, pull the most recent version of lightning from github
    ```
	/home/lightning/lightning/experimental/pylightweb/lightning# git pull
    ```
6.	Inside the lightning container, migrate the lightning tables into your postgres container
    ```
	/home/lightning/lightning/experimental/pylightweb/lightning# python manage.py migrate
    ```
7.	That's it! You can test the installation inside the lightning container
    ```
	/home/lightning/lightning/experimental/pylightweb/lightning# python manage.py test tile_library
    ```

