Folders
=======================

## getImportantGenes/ 
	scrapy for genetests site (not currently needed as GeneReviews and Ensembl provide their own annotations)

## lightning/
	contains the prototype website and models used to run lightning

How to Set-up a local lightning cluster:
=======================
## Notes: 
* We are aware this is a cumbersome installation. We are working to smooth the procedure out. 
* This will not populate the database with a tile library. For information on populating the database, see the README.md file in pylightweb/lightning/loadgenomes

## Procedure:
1.	Install python 2.7

2.	Install/update django
  * To check django installation:

		```
		$ python -c "import django; print(django.get_version())"
		1.6.5
		```
  * If this is wrong, run:

		```
		$ sudo pip install django==1.6.5
		```
  * For further instructions on proper installation of django, see <https://docs.djangoproject.com/en/1.6/topics/install/>

3.	Ensure checkout of the development branch (code that runs on a localhost): 

		```
		$ git checkout --track -b development origin/development
		```

4.	Install postgresql and the dependencies necessary to interact with django:

		```
		$ sudo apt-get install postgresql-9.3
		$ sudo apt-get install postgresql-server-dev-all
		$ sudo pip install psycopg2
		```

5.	Create users and database:

		```
		$ sudo -u postgres createuser -P $USER
		mypassword
		$ sudo -u createdb lightningdatabase
		```

6.	Edit lighting/experimental/pylightweb/lightning/lightning/settings.py
  * set: DBPW = "mypassword" (the password entered for createuser above)
  * set: 'USER': '$USER'

7.	Install nested-inlines:

		```
		$ sudo pip install -e git+git://github.com/Soaa-/django-nested-inlines.git#egg=django-nested-inlines
		```

8.	Create the needed tables:

		```
		lighting/experimental/pylightweb/lightning$ python manage.py syncdb
		```

