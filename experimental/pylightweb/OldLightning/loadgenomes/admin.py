from django.contrib import admin
#from nested_inlines.admin import NestedModelAdmin, NestedTabularInline

# We only want the annotations to be modifiable by the admin, not the tiles
from loadgenomes.models import Tile, TileVariant, VarAnnotation, TileLocusAnnotation

class AnnotationAdmin(admin.ModelAdmin):
    extra = 0
    fieldsets = [
        (None, {'fields':['annotation_type', 'source', 'annotation_text', 'phenotype']}),
        #('Time Data', {'fields':['created', 'last_modified'], 'classes': ['collapse']}),
    ]
    can_delete=False
    
class TileLocusAdmin(admin.ModelAdmin):
    extra = 0
    can_delete=False
    
class TileVarAdmin(admin.ModelAdmin):
    extra = 0
    #It would be nice to customize whether the tags are collapsed if the tags are actually different
    fieldsets = [
        (None, {'fields':['length', 'population_size', 'md5sum']}),
        ('Sequence', {'fields':['sequence'], 'classes':['collapse']}),
        ('Tags', {'fields':['start_tag', 'end_tag'], 'classes': ['collapse']}),
    ]
    can_delete=False

class TileAdmin(admin.ModelAdmin):
    list_display = ('getTileString', 'created')
    #search_fields = ['tilename']
    #inlines = [UpperLocusInLine,TileVarInLine,]
    can_delete=False
    
admin.site.register(Tile, TileAdmin)
admin.site.register(TileVariant, TileVarAdmin)
admin.site.register(TileLocusAnnotation, TileLocusAdmin)
admin.site.register(VarAnnotation, AnnotationAdmin)


