from django.contrib import admin

# We only want the annotations to be modifiable by the admin, not the tiles
from tile_library.models import Tile, TileVariant, TileLocusAnnotation, GenomeVariant

class GenomeVariantAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'chromosome_int', 'locus_start_int', 'created', 'last_modified')
    list_filter = ['last_modified']
    search_fields = ['names', 'info']
    extra = 0


class TileLocusAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'assembly_int', 'chromosome_int')
    list_filter = ['assembly_int', 'chromosome_int']
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
    list_display = ('get_string', 'created')
    can_delete=False

admin.site.register(Tile, TileAdmin)
admin.site.register(TileVariant, TileVarAdmin)
admin.site.register(TileLocusAnnotation, TileLocusAdmin)
admin.site.register(GenomeVariant, GenomeVariantAdmin)
