# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('genes', '0007_genexref_gene_review_phenotype_map'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genexref',
            name='gene_aliases',
            field=models.CharField(max_length=255, db_index=True),
        ),
        migrations.AlterField(
            model_name='ucsc_gene',
            name='chrom',
            field=models.PositiveSmallIntegerField(db_index=True, verbose_name=b'Chromosome Location', choices=[(1, b'chr1'), (2, b'chr2'), (3, b'chr3'), (4, b'chr4'), (5, b'chr5'), (6, b'chr6'), (7, b'chr7'), (8, b'chr8'), (9, b'chr9'), (10, b'chr10'), (11, b'chr11'), (12, b'chr12'), (13, b'chr13'), (14, b'chr14'), (15, b'chr15'), (16, b'chr16'), (17, b'chr17'), (18, b'chr18'), (19, b'chr19'), (20, b'chr20'), (21, b'chr21'), (22, b'chr22'), (23, b'chrX'), (24, b'chrY'), (25, b'chrM'), (26, b'Other')]),
        ),
        migrations.AlterField(
            model_name='ucsc_gene',
            name='tile_end_tx',
            field=models.BigIntegerField(db_index=True),
        ),
        migrations.AlterField(
            model_name='ucsc_gene',
            name='tile_start_tx',
            field=models.BigIntegerField(db_index=True),
        ),
    ]
