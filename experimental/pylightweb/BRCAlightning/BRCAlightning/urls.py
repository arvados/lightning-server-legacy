from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
                       #url(r'^$', 'BRCAlightning.views.home', name='home'),
                       url(r'^', include('home.urls', namespace="home")),
                       url(r'^genes/', include('genes.urls', namespace="genes")),
                       url(r'^library/', include('tile_library.urls', namespace="tile_library")),
                       url(r'^admin/', include(admin.site.urls)),
                       url(r'^map/', include('slippy.urls', namespace="slippy")),
                       url(r'^humans/', include('humans.urls', namespace="humans")),
                       url(r'^admin/', include(admin.site.urls)),
)
