import json
import os
import csv
import sys
sys.path.append("/home/sguthrie/lightning/experimental/pylightweb/lightning")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lightning.settings")

from django.utils import timezone

now = timezone.now()

human_fixtures = []

fileNames = []
for f in os.listdir("/home/sguthrie/abv"):
    if ".abv" in f:
        fileNames.append(f)

fileNames = sorted(fileNames)

ethn_parser = {    
    "American Indian / Alaska Native":"AMER_INDIAN_ALASKAN", 
    "Hispanic or Latino":"HISPANIC_LATINO",
    "Black or African American":"BLACK_AA",
    "Native Hawaiian or Other Pacific Islander":"HAWAIIAN_PACIFIC_ISLAND",
    "White":"WHITE", 
    "Asian":"ASIAN",
}
age_parser = {
    '0-9 years':0,
    '10-19 years':10,
    '20-29 years':20,
    '21-29 years':20,
    '30-39 years':30,
    '40-49 years':40,
    '50-59 years':50,
    '60-69 years':60,
    '70-79 years':70,
    '80-89 years':80,
    '90-99 years':90,
    '100-109 years':100,
    '110 years or up':110,
}

# Get Population data
subjects = {}
#Each subject has a name, sex, race, and position in the statistical analysis list
with open("ABVData.csv", 'rb') as surveyFile:
    surveyReader = csv.reader(surveyFile)
    for row in surveyReader:
        if row[0] == "Participant": #We are reading the header
            sex_i = row.index("Sex/Gender")
            race_i = row.index("Race/ethnicity")
            age_i = row.index("Year of birth")
        else:
            subjects[row[0]] = [row[sex_i], row[race_i], row[age_i]]

for fileIndex, f in enumerate(fileNames):
    humanName = f.split('.')[0]
    if humanName in subjects:
        gender, ethnicity, age = subjects[humanName]
        ethnicities = ethnicity.split(',')
        ethn_inp = ""
        for ethn in ethnicities:
            ethn = ethn.strip()
            if ethn in ethn_parser:
                ethn_inp+= ethn_parser[ethn]+","
            else:
                ethn_inp+= "OTHER:"+ethn+","
        if ethn_inp == "":
            ethn_inp = "UNKNOWN,"
        if gender in ['Male', 'male', 'MALE']:
            gender_inp = "MALE"
        elif gender in ['Female', 'female', 'FEMALE']:
            gender_inp = "FEMALE"
        elif gender in ['trans', 'trans*', 'TRANS', 'TRANS*', 'Trans', 'Trans*']:
            gender_inp = "TRANS"
        else:
            gender_inp = 'UNKNOWN'

        if age not in age_parser:
            try:
                age_inp = ((now.year - int(age))/10)*10
            except:
                age_inp = -1
        else:
            age_inp = age_parser[age]
    else:
        ethn_inp = "UNKNOWN"
        gender_inp = "UNKNOWN"
        age_inp = -1
    human_json = { "model": "humans.human",
                   "pk": fileIndex+1,
                   "fields":{
                       "phaseA_npy":"numpy_abvs/"+humanName+"_phaseA.npy",
                       "phaseB_npy":"numpy_abvs/"+humanName+"_phaseB.npy",
                       "index_in_big_file":fileIndex,
                       "name":humanName,
                       "chromosomal_sex":"UNKNOWN",
                       "gender": gender_inp,
                       "age_range":age_inp,
                       "ethnicity":ethn_inp,
                       "created":str(now),
                       "updated":str(now),
                   }
                 }
    human_fixtures.append(human_json)

with open('fixtures/initial_data.json', 'w') as f:
    json.dump(human_fixtures, f)
