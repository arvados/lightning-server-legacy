from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from api import views

urlpatterns = [
    url(r'^tilevariants/$', views.TileVariantList.as_view()),
    url(r'^tilevariants/(?P<pk>[0-9]+)/$', views.TileVariantDetail.as_view()),
    url(r'^population/$', views.PopulationVariantQuery.as_view(), name="variant_query"),
]

urlpatterns=format_suffix_patterns(urlpatterns)
