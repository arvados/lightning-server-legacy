from django.shortcuts import render

from humans.models import Human, IndividualGroup
# Create your views here.

ethn_parser = {
    "UNKNOWN":"UNKNOWN",
    "AMER_INDIAN_ALASKAN":"American Indian / Alaska Native",
    "HISPANIC_LATINO":"Hispanic or Latino",
    "BLACK_AA":"Black or African American",
    "HAWAIIAN_PACIFIC_ISLAND":"Native Hawaiian or Other Pacific Islander",
    "WHITE":"White",
    "ASIAN":"Asian",
    }

def individuals(request):
    all_humans = Human.objects.all().order_by('name')
##    for hu in all_humans:
##        ethn = hu.ethnicity.split(',')
##        for ethn
##        readable_ethn = ethn_parse[ethn]
    return render(request, "individuals.html", {'all_humans':all_humans})

#def one_person(request):
#def groups(request):
#    poss_groups = IndividualGroup.objects.all()
    
        
