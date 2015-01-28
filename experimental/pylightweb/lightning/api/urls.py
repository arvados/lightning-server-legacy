from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from api import views

urlpatterns = [
    url(r'^$', views.documentation, name="documentation"),
    url(r'^tilevariants/(?P<hex_string>[0-9a-f\.]+)/$', views.TileVariantQuery.as_view(), name="tile_variant_query"),
    url(r'^loci/(?P<tile_hex_string>[0-9a-f\.]+)/$', views.TileLocusAnnotationList.as_view(), name="locus_query"),
    url(r'^between_loci/$', views.PopulationVariantQueryBetweenLoci.as_view(), name="pop_between_loci"),
    url(r'^around_locus/$', views.PopulationVariantQueryAroundLocus.as_view(), name="pop_around_locus"),
]

urlpatterns=format_suffix_patterns(urlpatterns)
