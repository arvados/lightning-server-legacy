from django.conf.urls import patterns, url

from variant_query import views

urlpatterns = patterns('',
                       url(r'^$', views.index, name='index')
                       )
