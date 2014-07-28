from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', include('slippy.urls', namespace="slippy")),
    url(r'^loadGenomes/', include('loadGenomes.urls', namespace="loadGenomes")),
    url(r'^admin/', include(admin.site.urls)),
)
