## Notes: 
* Adding data using fixtures takes a while and uses 30MB in postgres
* To add your own data, see the scripts and README in pylightweb/lightning/loadgenomes

## Procedure to load path data containing BRCA genes for 3 humans:
1. To add predefined fixtures.
		```
		pylightweb/lightning$ python manage.py loaddata brca1 brca2
		```

