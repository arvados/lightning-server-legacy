import numpy as np
import os.path
from django.shortcuts import render, get_object_or_404

from humans.models import Human, IndividualGroup

def individuals(request):
    all_humans = Human.objects.all().order_by('name')
    return render(request, "individuals.html", {'all_humans':all_humans})

def one_person(request, human_id):
    person = get_object_or_404(Human, pk=human_id)
    phased = "Not sequenced"
    data = {'person':person, 'phased':phased}
    if os.path.isfile(person.phaseA_npy.path) and os.path.isfile(person.phaseB_npy.path):
        phased = "Phased"
        A = np.load(person.phaseA_npy.path)
        B = np.load(person.phaseB_npy.path)
        data['A'] = A
        data['B'] = B
    if os.path.isfile(person.phaseA_npy.path) and not os.path.isfile(person.phaseB_npy.path):
        phased = "Unphased"
        A = np.load(person.phaseA_npy.path)
        data['A'] = A
    return render(request, "person.html", data)
        
        


#def groups(request):
#    poss_groups = IndividualGroup.objects.all()
    
        
