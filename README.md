Lightning
=========

How to Set-up a local lightning cluster:
=======================
## Notes:
* This will **not** populate the database with a tile library or population. These capabilities are under development.
* An official Curoverse/Arvados docker image is in development.

## Procedure:
1.	Install docker (https://docs.docker.com/installation/)

2.	Pull sguthrie/lightning

		$ sudo docker pull sguthrie/lightning

3.  Run sguthrie/lightning interactively using /bin/bash

		$ sudo docker run -t -i sguthrie/lightning /bin/bash

3.	Ensure the current working directory is correct:

		# cd home/lightning/lightning/experimental/pylightweb/lightning/

4.	Pull the most recent version of lightning from github

		/home/lightning/lightning/experimental/pylightweb/lightning# git pull

5.	That's it! All the capabilities of lightning are available. You can run a server using:

		/home/lightning/lightning/experimental/pylightweb/lightning# python manage.py runserver

And you can test the installation using:

		/home/lightning/lightning/experimental/pylightweb/lightning# python manage.py test
