from django.contrib import admin

from loadgenes.models import Gene

class GeneAdmin(admin.ModelAdmin):
    list_display = ('gene_name', 'feature', 'source', 'seqname')
    list_filter = ['feature', 'source', 'seqname']
    search_fields = ['gene_name']
    fieldsets = [
        (None, {'fields': ['source', 'feature']}),
        ('Location information', {'fields':['seqname', 'startCGF', 'endCGF']}),
        ('Gene information', {'fields':['gene_name', 'gene_biotype', 'gene_source', 'gene_id']}),
        ('Transcript information', {'fields':['transcript_name', 'transcript_biotype',
                                              'transcript_source', 'transcript_id'],
                                    'classes': ['collapse']}),
        ('Exon information', {'fields':['exon_id', 'exon_number'],
                              'classes': ['collapse']}),
        ('Protein information', {'fields':['protein_id'],
                                 'classes':['collapse']}),
        ('Other information', {'fields':['strand', 'frame', 'score']}),
    ]

admin.site.register(Gene, GeneAdmin)
