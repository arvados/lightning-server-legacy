from django.contrib import admin

# We only want the annotations to be modifiable by the admin, not the tiles
from tile_library.models import Tile, TileVariant, VarAnnotation, TileLocusAnnotation

class AnnotationAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'annotation_type', 'created', 'last_modified')
    list_filter = ['last_modified', 'annotation_type']
    search_fields = ['annotation_text', 'phenotype']
    extra = 0
    fieldsets = [
        (None, {'fields':['annotation_type', 'source', 'annotation_text', 'phenotype']}),
        ('Time Data', {'fields':['created', 'last_modified']}),
    ]
    
class TileLocusAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'assembly', 'chromosome')
    list_filter = ['assembly', 'chromosome']
    extra = 0
    can_delete=False
    
class TileVarAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'length', 'md5sum')
    extra = 0
    #It would be nice to customize whether the tags are collapsed if the tags are actually different
    fieldsets = [
        (None, {'fields':['length', 'variant_value', 'md5sum']}),
        ('Sequence', {'fields':['sequence']}),
        ('Tags', {'fields':['start_tag', 'end_tag']}),
    ]
    can_delete=False

class TileAdmin(admin.ModelAdmin):
    list_display = ('getTileString', 'created')
    can_delete=False
    
admin.site.register(Tile, TileAdmin)
admin.site.register(TileVariant, TileVarAdmin)
admin.site.register(TileLocusAnnotation, TileLocusAdmin)
admin.site.register(VarAnnotation, AnnotationAdmin)
