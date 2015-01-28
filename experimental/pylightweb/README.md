Warning:
=======================
We provide a few fixtures for testing and installation of genes of interest. Adding multiple fixtures at once will create edge cases and unexpected behavior of the application. To interact with a complete installation of data, visit http://lightning-dev3.curoverse.com


Folders
=======================

## lightning/
	contains the prototype website and models used to run lightning

How to Set-up a local lightning cluster:
=======================
## Notes:
* We are aware this is a cumbersome installation. We are working to smooth the procedure out.
* This will not populate the database with a tile library. For information on populating the database, see the README.md file in pylightweb/lightning/tile_library

## Procedure:
1.	Install python 2.7

2.	Install/update django
  * To check django installation:

		```
		$ python -c "import django; print(django.get_version())"
		1.7
		```
  * If this is wrong, run:

		```
		$ sudo pip install django
		```
  * For further instructions on proper installation of django, see <https://docs.djangoproject.com/en/1.7/topics/install/>

3. Install selenium (for testing)

		```
		$ sudo pip install selenium
		```

3.	Ensure checkout of the development branch (code that runs on a localhost):

		$ git checkout --track -b development origin/development
4.	Install postgresql (version 9.1 to 9.3 will work) and the dependencies necessary to interact with django:

		$ sudo apt-get install postgresql-9.3
		$ sudo apt-get install postgresql-server-dev-all
		$ sudo pip install psycopg2
5.	Create users and database:

		$ sudo -u postgres createuser -P $USER
		mypassword
		$ sudo -u postgres createdb lightningdatabase
6.	Edit lighting/experimental/pylightweb/lightning/lightning/settings.py
  * set: DBPW = "mypassword" (the password entered for createuser above)
  * set: 'USER': '$USER'

7.	Create the needed tables:

		lighting/experimental/pylightweb/lightning$ python manage.py migrate
