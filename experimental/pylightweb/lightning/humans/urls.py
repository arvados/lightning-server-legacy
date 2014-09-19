from django.conf.urls import patterns, url

from humans import views

urlpatterns = patterns('',
                       url(r'^$', views.individuals, name='individuals'),
                       )
