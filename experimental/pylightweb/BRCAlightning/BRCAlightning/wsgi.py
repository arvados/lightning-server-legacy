"""
WSGI config for BRCAlightning project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/
"""

import os, sys
sys.path.append('/home/sguthrie/pylightweb/')
sys.path.append('/home/sguthrie/pylightweb/BRCAlightning/')
#os.environ["DJANGO_SETTINGS_MODULE"] = "{{ project_name }}.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BRCAlightning.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
