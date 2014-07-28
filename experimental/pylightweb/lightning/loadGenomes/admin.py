from django.contrib import admin
from nested_inlines.admin import NestedModelAdmin, NestedTabularInline

# We only want the annotations to be modifiable by the admin, not the tiles
from loadGenomes.models import Tile, TileVariant, TileVarAnnotation, varLocusAnnotation, tileLocusAnnotation

class AnnotationInLine(NestedTabularInline):
    model = TileVarAnnotation
    extra = 2
    can_delete=False

class LocusInLine(NestedTabularInline):
    model = varLocusAnnotation
    extra = 0
    can_delete=False
    
class UpperLocusInLine(NestedTabularInline):
    model = tileLocusAnnotation
    extra = 0
    can_delete=False
    
class TileVarInLine(NestedTabularInline):
    model = TileVariant
    extra = 0
    #Awesome thing would be to customize whether the tags are collapsed if the tags are actually different
    fieldsets = [
        (None, {'fields':['tile', 'reference', 'hasGap', 'hasGapOnTag', 'length', 'populationSize', 'sequence']}),
        ('Tags', {'fields':['startTag', 'endTag', 'md5sum'], 'classes': ['collapse']}),
    ]
    inlines = [LocusInLine, AnnotationInLine,]
    can_delete=False

class TileAdmin(NestedModelAdmin):
    list_display = ('getTileString', 'created')
    #search_fields = ['tilename']
    inlines = [TileVarInLine,UpperLocusInLine,]
    can_delete=False
    
admin.site.register(Tile, TileAdmin)

