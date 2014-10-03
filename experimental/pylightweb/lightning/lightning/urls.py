from django.conf.urls import patterns, include, url

from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
                       url(r'^', include('home.urls', namespace="home")),
                       #url(r'^slippy/', include('slippy.urls', namespace="slippy")),
                       #url(r'^loadgenes/', include('loadgenes.urls', namespace="loadgenes")),
                       url(r'^library/', include('tile_library.urls', namespace="tile_library")),
                       #url(r'^humans/', include('humans.urls', namespace="humans")),
                       url(r'^admin/', include(admin.site.urls)),
)
