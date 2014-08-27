from django.conf.urls import patterns, url

from slippy import views

urlpatterns = patterns('',
                       url(r'^$', views.index, name='index'),
                       url(r'^search/$', views.simplesearch, name='simplesearch'),
                       #url(r'^search/?geneName=(?P<text>\w+)/$', views.search, name='search'),
                       )
