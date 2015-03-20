from django.conf.urls import patterns, url

from humans import views

urlpatterns = patterns('',
                       url(r'^$', views.individuals, name='individuals'),
                       url(r'^(?P<human_id>\d+)/$', views.one_person, name='one_person'),
                       )
