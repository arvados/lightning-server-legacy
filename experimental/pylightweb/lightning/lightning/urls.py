from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
                       url(r'^$', 'lightning.views.home', name='home'),
                       url(r'^help/$', 'lightning.views.help', name='help'),
                       url(r'^query/', include('api_gui.urls', namespace='population_sequence_query')),
                       url(r'^api/', include('api.urls', namespace='api')),
)
