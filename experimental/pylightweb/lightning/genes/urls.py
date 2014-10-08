from django.conf.urls import patterns, url

from genes import views

urlpatterns = patterns('',
                       url(r'^$', views.current_gene_names, name='names'),
                       url(r'^(?P<xref_id>\d+)/$', views.specific_gene, name='specific'),
                       )
