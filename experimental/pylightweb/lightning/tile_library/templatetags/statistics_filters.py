from django import template
import urllib

register = template.Library()

@register.filter
def get_reference_length(position):
    reference = position.variants.filter(variant_value=0).first()
    return reference.length

@register.simple_tag
def url_replace(request, field, value):
    """request expected to be request.GET """
    dict_ = request.copy()
    dict_[field] = value
    return urllib.urlencode(dict_)

