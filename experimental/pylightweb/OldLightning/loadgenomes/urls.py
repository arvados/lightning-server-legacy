from django.conf.urls import patterns, url

from loadgenomes import views

urlpatterns = patterns('',
                       url(r'^$', views.statistics, name='statistics'),
                       url(r'^getStats/$', views.loadstatistics, name='loadstatistics'),
                       url(r'^(?P<annotation_id>\d+)/$', views.detail, name='detail'),
                       url(r'^(?P<annotation_id>\d+)/review/$', views.review, name='review'),
                       url(r'^(?P<tile_id>\d+)/annotate/$', views.annotate, name='annotate'),
                       url(r'^upload/$', views.upload, name='upload'),
                       )
