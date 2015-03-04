from django.conf.urls import patterns, url

from api_gui import views

urlpatterns = patterns('',
                       url(r'^around/$', views.around_locus_query_view, name='around_locus_form'),
                       url(r'^between/$', views.between_loci_query_view, name='between_loci_form')
                       )
