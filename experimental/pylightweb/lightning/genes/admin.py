from django.contrib import admin

from genes.models import UCSC_Gene, GeneXRef
# Register your models here.

class xRefAdmin(admin.StackedInline):
    model = GeneXRef
    extra = 0

class UCSCGeneAdmin(admin.ModelAdmin):
    inlines = [xRefAdmin]
    list_display = ('__unicode__', 'chrom', 'tile_start_tx', 'tile_end_tx', 'exon_count', 'get_description') 
    list_filter = ['chrom']
    
admin.site.register(UCSC_Gene, UCSCGeneAdmin)

