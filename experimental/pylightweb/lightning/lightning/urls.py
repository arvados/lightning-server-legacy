from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^slippy/', include('slippy.urls', namespace="slippy")),
    #url(r'^loadgenes/', include('loadgenes.urls', namespace="loadgenes")),
    url(r'^loadgenomes/', include('loadgenomes.urls', namespace="loadgenomes")),
    url(r'^admin/', include(admin.site.urls)),
)
