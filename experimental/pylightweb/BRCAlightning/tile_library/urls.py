from django.conf.urls import patterns, url

from tile_library import views

urlpatterns = patterns('',
                       url(r'^$', views.overall_statistics, name='statistics'),
                       url(r'^rsID/(?P<rs_id>[dbsnp0-9:r]+)/$', views.rs_id_search, name='rs_id_search'),
                       url(r'^rsID/(?P<rs_id>[dbsnp0-9:r]+)/exact/$', views.rs_id_search_exact, name='rs_id_search_exact'),
                       url(r'^rsID/(?P<rs_id>[dbsnp0-9:r]+)/(?P<position_int>\d+)/$', views.rs_id_tile_view, name='rs_id_tile_view'),
                       url(r'^rsID/(?P<rs_id>[dbsnp0-9:r]+)/(?P<position_int>\d+)/exact/$', views.rs_id_tile_view_exact, name='rs_id_tile_view_exact'),
                       url(r'^protein/$', views.all_protein_changes, name='all_protein_changes'),
                       url(r'^protein/(?P<protein>\w+)/$', views.protein_search, name='protein_search'),
                       url(r'^protein/(?P<protein>\w+)/(?P<position_int>\d+)/$', views.protein_tile_view, name='protein_tile_view'),
                       url(r'^(?P<chr_int>\d+)/$', views.chr_statistics, name='chr_statistics'),
                       url(r'^(?P<chr_int>\d+)/(?P<path_int>\d+)/$', views.path_statistics, name='path_statistics'),
                       url(r'^(?P<chr_int>\d+)/(?P<path_int>\d+)/(?P<tilename>\d+)/$', views.tile_view, name='tile_view'),
                       url(r'^locus/(?P<assembly_int>\d+)/(?P<chr_int>\d+)/(?P<lower_int>\d+)/(?P<upper_int>\d+)/$', views.view_locus_range, name='view_locus_range'),
                       url(r'^locusvariant/(?P<assembly_int>\d+)/(?P<chr_int>\d+)/(?P<locus>\d+)/(?P<reference>\w+)/(?P<mutation>\w+)/$', views.tile_variant_view, name='tile_variant_view'),
                       url(r'^position/(?P<tilename>\d+)/$', views.abbrev_tile_view, name='abbrev_tile_view'),
                       url(r'^gene/(?P<gene_xref_id>\d+)/$', views.gene_view, name='gene_view'),
                       url(r'^gene/(?P<gene_xref_id>\d+)/(?P<tilename>\d+)/$', views.tile_in_gene_view, name='tile_in_gene_view'),
##                       url(r'^(?P<annotation_id>\d+)/$', views.detail, name='detail'),
##                       url(r'^(?P<annotation_id>\d+)/review/$', views.review, name='review'),
##                       url(r'^(?P<tile_id>\d+)/annotate/$', views.annotate, name='annotate'),
##                       url(r'^upload/$', views.upload, name='upload'),
                       )
