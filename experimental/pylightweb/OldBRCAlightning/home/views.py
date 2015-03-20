from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse

from django.shortcuts import render_to_response
from django.template import RequestContext
import string
import re

from genes.models import GeneXRef
from tile_library.models import Tile
import tile_library.functions as fns
import genes.functions as gene_fns

def parse_location(location_text):
    parsed_text = location_text.strip().split(':')
    if len(parsed_text) == 1:
        regex = 'chr([1-9][0-9]?)([pq][0-9]+\.*[0-9]*)'
        m = re.match(regex, location_text)
        assert m != None, "%s doesn't match the expected cytoband format (chr13q11.1)" % location_text
        chr_int = int(m.group(1))
        cytomap = m.group(2)
        cytobands_to_look = Tile.CYTOMAP[Tile.CHR_PATH_LENGTHS[chr_int-1]:Tile.CHR_PATH_LENGTHS[chr_int]]
        if cytomap not in cytobands_to_look:
            return False, (cytomap + ' not recognized as a band in chromosome ' + str(chr_int) )
        else:
            path_int = cytobands_to_look.index(cytomap)+Tile.CHR_PATH_LENGTHS[chr_int-1]
            return True, ('path', chr_int, path_int)
    else:
        chr_int = int(parsed_text[0].lstrip('chr'))
        parsed_loci = parsed_text[1].replace(',', '').split('-')
        print parsed_loci
        if len(parsed_text) == 2:
            if len(parsed_loci) != 2:
                return False, ('Unable to parse '+parsed_text[1]+' as a locus range')
            else:
                lower_int = min(parsed_loci)
                upper_int = max(parsed_loci)
                return True, ('locus_range', chr_int, lower_int, upper_int)
        elif len(parsed_text) == 4:
            locus = parsed_text[1].replace(',','')
            reference = parsed_text[2]
            variant = parsed_text[3]
            return True, ('variant', chr_int, locus, reference, variant)
        else:
            return False, ("Unable to recognize the location/variant")

def index(request):
    search_name = request.GET.get('search')
    search_type = request.GET.get('searchtype')
    search_target = request.GET.get('searchtarget')
    if search_name == None or search_type == None or search_target == None:
        return render(request, 'home/index.html', {})
    else:
        if search_target == 'genes':
            if search_type == 'for_gene':
                #Send on the request to genes:names (in filter form)
                return HttpResponseRedirect(reverse('genes:names')+"?filter="+search_name)
            elif search_type == 'for_gene_review':
                #Send on the request to genes:names (in phenotype form)
                return HttpResponseRedirect(reverse('genes:names')+"?phenotype="+search_name)
            else:
                #Incorrect formatting for ending
                return render(request, 'home/index.html', {'alert':'Incorrect search type for the response target of gene'})
        elif search_target == 'slippy_map':
            #return render(request, 'home/index.html', {'alert':'Slippy Map not loaded for BRCA data yet!'})
            if search_type == 'for_gene':
                #Send on the request to slippy:map (in filter form)
                return HttpResponseRedirect(reverse('slippy:slippymap')+"?filter="+search_name)
            elif search_type == 'for_gene_review':
                #Send on the request to slippy:map (in phenotype form)
                return HttpResponseRedirect(reverse('slippy:slippymap')+"?phenotype="+search_name)
            elif search_type in ['by_path', 'by_position', 'by_location']:
                #Haven't implemented
                return render(request, 'home/index.html', {'alert':'Not implemented yet'})
            else:
                #Incorrect formatting for slippy_map target
                return render(request, 'home/index.html', {'alert':'Incorrect search type for the response target of slippy_map'})
        elif search_target == 'tile_library':
            if search_type == 'for_gene':
                #Check we can load gene into tile library format: only one gene name match and all gene transcripts are overlapping
                distinct_genes = GeneXRef.objects.using('entire').order_by('gene_aliases').distinct('gene_aliases').filter(gene_aliases__istartswith=search_name)
                genes = GeneXRef.objects.using('entire').filter(gene_aliases__istartswith=search_name).order_by('gene__chrom', 'description')
                if not distinct_genes.exists():
                    distinct_genes = GeneXRef.objects.using('entire').order_by('gene_aliases').distinct('gene_aliases').filter(gene_aliases__icontains=search_name)
                    genes = GeneXRef.objects.using('entire').filter(gene_aliases__icontains=search_name).order_by('gene__chrom', 'description')
                
                if distinct_genes.count() > 1:
                    return render(request, 'home/index.html', {'alert':'Multiple genes match that name. Try using the response format Gene View'})
                else:
                    gene_xref_id = distinct_genes.first().id
                    overlapping_genes = gene_fns.split_genes_into_groups(genes)
                    if len(overlapping_genes) > 1:
                        return render(request, 'home/index.html', {'alert':'That gene name spans multiple loci. Try searching in Search for Gene'})
                    else:
                        return HttpResponseRedirect(reverse('tile_library:gene_view', args=(gene_xref_id,)))

            elif search_type == 'for_gene_review':
                #Check we can load gene into tile library format: only one gene name match and all gene transcripts are overlapping
                distinct_genes = GeneXRef.objects.using('entire').order_by('gene_aliases').distinct('gene_aliases').filter(gene_review_phenotype_map__icontains=search_name)
                genes = GeneXRef.objects.using('entire').filter(gene_review_phenotype_map__icontains=search_name)
                if distinct_genes.count() > 1:
                    return render(request, 'home/index.html', {'alert':'Multiple genes contain that text in their Gene Review article Title. Try searching in Search for Gene'})
                else:
                    gene_xref_id = distinct_genes.first().id
                    overlapping_genes = gene_fns.split_genes_into_groups(genes)
                    if len(overlapping_genes) > 1:
                        return render(request, 'home/index.html', {'alert':'The gene containing this text in its Gene Review article Title spans multiple loci. Try searching in Search for Gene'})
                    else:
                        return HttpResponseRedirect(reverse('tile_library:gene_view', args=(gene_xref_id,)))
            
            elif search_type == 'by_path':
                if search_type == "":
                    return render(request, 'home/index.html', {'alert':"Enter a path to search for"})
                try:
                    path_int = int(search_name, 16)
                    chr_int = fns.get_chromosome_int_from_path_int(path_int)
                except Exception as e:
                    return render(request, 'home/index.html', {'alert':str(e)})
                return HttpResponseRedirect(reverse('tile_library:path_statistics', args=(chr_int, path_int)))

            elif search_type == 'by_position':
                try:
                    split_by_decimals = search_name.split('.')
                    tile_int = int(string.join(split_by_decimals, ''), 16)
                    if len(split_by_decimals) > 1:
                        path_int = int(split_by_decimals[0], 16)
                    else:
                        path_int = int(search_name.zfill(9)[:3], 16)
                    chr_int = fns.get_chromosome_int_from_path_int(path_int)
                except Exception as e:
                    return render(request, 'home/index.html', {'alert':str(e)})
                return HttpResponseRedirect(reverse('tile_library:tile_view', args=(chr_int, path_int, tile_int)))
            
            elif search_type == 'by_location':
                parsable, retval = parse_location(search_name)
                if parsable:
                    if retval[0] == 'path':
                        return HttpResponseRedirect(reverse('tile_library:path_statistics', args=(retval[1], retval[2])))
                    elif retval[0] == 'locus_range':
                        #Assembly 19, chromosome, begin_int, end_int
                        return HttpResponseRedirect(reverse('tile_library:view_locus_range', args=(19, retval[1], retval[2], retval[3])))
                    elif retval[0] == 'variant':
                        return HttpResponseRedirect(reverse('tile_library:tile_variant_view', args=(19, retval[1], retval[2], retval[3], retval[4])))
                    else:
                        raise Exception("Unable to understand the parse_location return value")
                else:
                    return render(request, 'home/index.html', {'alert':retval})

            elif search_type == 'by_rs_id':
                if search_name != "":
                    return HttpResponseRedirect(reverse('tile_library:rs_id_search', args=(search_name,)))
                else:
                    return render(request, 'home/index.html', {'alert':'Enter an rsID'})

            elif search_type == 'by_exact_rs_id':
                if search_name != "":
                    return HttpResponseRedirect(reverse('tile_library:rs_id_search_exact', args=(search_name,)))
                else:
                    return render(request, 'home/index.html', {'alert':'Enter an rsID'})
                
            elif search_type == 'by_protein_affected':
                if search_name == "":
                    return HttpResponseRedirect(reverse('tile_library:all_protein_changes'))
                else:
                    return HttpResponseRedirect(reverse('tile_library:protein_search', args=(search_name,)))
            else:
                return render(request, 'home/index.html', {'alert':'Did not understand search type'})
        elif search_target == 'humans':
            return render(request, 'home/index.html', {'alert':'Not implemented yet'})
        else:
            return render(request, 'home/index.html', {'alert':'Did not understand search target'})


def help_me(request):
    return render(request, 'home/help.html',{})
