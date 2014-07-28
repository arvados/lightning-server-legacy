from django.conf.urls import patterns, url

from slippy import views

urlpatterns = patterns('',
                       url(r'^$', views.index, name='index'),
                       )
