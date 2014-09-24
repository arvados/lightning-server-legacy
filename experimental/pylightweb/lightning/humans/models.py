from django.db import models


class IndividualGroup(models.Model):
    """
    Implements a group of individuals. Roughly follows GAIndividualGroup from org.ga4gh

    Needs some better specifications:
        group_type: needs choices
        info: needs choices or some form of possible keys
    
    """
    name = models.CharField(max_length=100)
    description = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    group_type = models.CharField(max_length=100)
    info = models.TextField()

class Human(models.Model):
    """
    Implements a human object. Roughly follows GAIndividual from org.ga4gh

    Reasons for variation from the schema (as defined on 2014-09-18):
        name: currently PGP id and limited to 8 characters
        description: unsure of meaning
        species: predefined for this table, since all are human
        developmentalStage: not implemented well by Uberon
        diseases: different implementation, possibly?
        phenotypes: different implementation?
        stagingSystem: unsure of meaning
        strain: N/A
        info: currently hardcoded into database

    ETHNICITY_CHOICES = (
        (UNKNOWN, Unknown), #in the case of no response
        (AMER_INDIAN_ALASKAN, American Indian / Alaska Native),
        (HISPANIC_LATINO, Hispanic or Latino),
        (BLACK_AA, Black or African American),
        (HAWAIIAN_PACIFIC_ISLAND, Native Hawaiian or Other Pacific Islander),
        (WHITE, White),
        (ASIAN, Asian),
    )
    
    """
    XX = 'XX'
    XY = 'XY'
    XX_XY = 'XX/XY'
    XXX = 'XXX'
    XXY = 'XXY'
    OTHER = 'OTHER'
    UNKNOWN = 'UNKNOWN'
    CHR_SEX_CHOICES = (
        (XX, XX),
        (XY, XY),
        (XX_XY, XX_XY),
        (XXX, XXX),
        (XXY, XXY),
        (OTHER, 'Other'),
        (UNKNOWN, 'Unknown'),
    )
    MALE = "MALE"
    FEMALE = "FEMALE"
    TRANS = "TRANS"
    GENDER_CHOICES = (
        (MALE, 'Male'),
        (FEMALE, 'Female'),
        (TRANS, 'Trans*'),
        (OTHER, 'Other'),
        (UNKNOWN, 'Unknown'),
    )
    AGE_RANGE_CHOICES = (
        (-1, 'Unknown'),
        (0, '0-9 years'),
        (10, '10-19 years'),
        (20, '20-29 years'),
        (30, '30-39 years'),
        (40, '40-49 years'),
        (50, '50-59 years'),
        (60, '60-69 years'),
        (70, '70-79 years'),
        (80, '80-89 years'),
        (90, '90-99 years'),
        (100, '100-109 years'),
        (110, '110 years or up'),
    )
    ethn_parser = {
        "AMER_INDIAN_ALASKAN":"American Indian / Alaska Native",
        "HISPANIC_LATINO":"Hispanic or Latino",
        "BLACK_AA":"Black or African American",
        "HAWAIIAN_PACIFIC_ISLAND":"Native Hawaiian or Other Pacific Islander",
        "WHITE":"White",
        "ASIAN":"Asian",
    }


    phaseA_npy = models.FileField(upload_to='numpy_abvs', verbose_name="Numpy-readable ABV file (Phase A or unphased)")
    phaseB_npy = models.FileField(upload_to='numpy_abvs', verbose_name="Numpy-readable ABV file (Phase B)", blank=True, null=True)
    index_in_big_file = models.PositiveIntegerField()
    groups = models.ManyToManyField(IndividualGroup, related_name="groupIds", blank=True, null=True)
    name = models.CharField(max_length=8, verbose_name="PGP id", blank=True, null=True, editable=False)
    chromosomal_sex = models.CharField(max_length=10, choices=CHR_SEX_CHOICES)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    date_of_birth = models.DateTimeField(blank=True, null=True)
    age_range = models.IntegerField(choices=AGE_RANGE_CHOICES)
    ethnicity = models.TextField() #Meant to be like CSV - see ETHNICITY_CHOICES

    def __unicode__(self):
        return self.name
    def human_readable_sex(self):
        for choice in self.CHR_SEX_CHOICES:
            if choice[0] == self.chromosomal_sex:
                return choice[1]
        raise Exception("Database error: '%s' not in CHR_SEX_CHOICES" % self.chromosomal_sex)
    def human_readable_gender(self):
        for choice in self.GENDER_CHOICES:
            if choice[0] == self.gender:
                return choice[1]
        raise Exception("Database error: '%s' not in GENDER_CHOICES" % self.gender)
    def human_readable_age_range(self):
        for choice in self.AGE_RANGE_CHOICES:
            if choice[0] == self.age_range:
                return choice[1]

        return "broken"
        #raise Exception("Database error: '%i' not in AGE_RANGE_CHOICES" % self.age_range)
    def human_readable_ethnicity_for_checkboxes(self):
        my_ethn = self.ethnicity.split(',')
        retval = []
        if "UNKNOWN" in my_ethn:
            return [{'name':'Unknown','value':True}]
        for ethn in self.ethn_parser:
            if ethn in my_ethn:
                retval.append({'name':self.ethn_parser[ethn],'value':True})
            else:
                retval.append({'name':self.ethn_parser[ethn],'value':False})
        for ethn in my_ethn:
            if "OTHER" in ethn:
                readable = ethn.split(":")[-1]
                retval.append({'name':"Other: "+readable,'value':True})
        return retval

    def human_readable_ethnicity_terse(self):
        my_ethn = self.ethnicity.split(',')
        if "UNKNOWN" in my_ethn:
            return ['Unknown']
        else:
            retval = []
            for ethn in my_ethn:
                if "OTHER" in ethn:
                    readable = ethn.split(":")[-1]
                    retval.append("Other: "+readable)
                elif ethn in self.ethn_parser:
                    retval.append(self.ethn_parser[ethn])
            return retval
            
    
    
    
