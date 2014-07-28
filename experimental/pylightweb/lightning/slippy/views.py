from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.http import Http404

#from loadGenomes.models import TileVarAnnotation

def index(request):
    return render(request, 'index.html', {})
