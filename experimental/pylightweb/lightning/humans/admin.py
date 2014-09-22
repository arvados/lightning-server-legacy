from django.contrib import admin

from humans.models import Human, IndividualGroup

class HumanAdmin(admin.ModelAdmin):
    list_display = ('name', 'gender', 'age_range')
    can_delete = False


class IndividualGroupAdmin(admin.ModelAdmin):
    pass

admin.site.register(Human, HumanAdmin)
admin.site.register(IndividualGroup, IndividualGroupAdmin)
