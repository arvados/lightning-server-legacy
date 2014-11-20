from django.conf.urls import patterns, url

from home import views

urlpatterns = patterns('',
                       url(r'^$', views.index, name='index'),
                       url(r'^help/$', views.help_me, name='help'),
                       )
