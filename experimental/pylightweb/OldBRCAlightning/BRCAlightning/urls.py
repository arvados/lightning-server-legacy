from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
                       url(r'^$', 'BRCAlightning.views.home', name='home'),
                       url(r'^help/$', 'BRCAlightning.views.help', name='help'),
                       url(r'^query/', include('variant_query.urls', namespace='population_sequence_query')),
                       url(r'^api/', include('api.urls', namespace='api')),
)
