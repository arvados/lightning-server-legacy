from django.conf.urls import patterns, url

from tile_library import views

urlpatterns = patterns('',
                       url(r'^$', views.overall_statistics, name='statistics'),
                       url(r'^(?P<chr_int>\d+)/$', views.chr_statistics, name='chr_statistics'),
                       url(r'^(?P<chr_int>\d+)/(?P<path_int>\d+)/$', views.path_statistics, name='path_statistics'),
                       url(r'^(?P<chr_int>\d+)/(?P<path_int>\d+)/(?P<tilename>\d+)/$', views.tile_view, name='tile_view'),
    
##                       url(r'^(?P<annotation_id>\d+)/$', views.detail, name='detail'),
##                       url(r'^(?P<annotation_id>\d+)/review/$', views.review, name='review'),
##                       url(r'^(?P<tile_id>\d+)/annotate/$', views.annotate, name='annotate'),
##                       url(r'^upload/$', views.upload, name='upload'),
                       )
