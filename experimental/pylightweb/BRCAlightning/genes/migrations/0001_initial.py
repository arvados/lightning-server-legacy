# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0002_auto_20141002_1101'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneXRef',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('mrna', models.CharField(max_length=255)),
                ('sp_id', models.CharField(max_length=255)),
                ('sp_display_id', models.CharField(max_length=255)),
                ('gene_aliases', models.CharField(max_length=255)),
                ('ref_seq', models.CharField(max_length=255)),
                ('prot_acc', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('rfam_acc', models.CharField(max_length=255)),
                ('trna_name', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UCSC_Gene',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ucsc_gene_id', models.CharField(max_length=255)),
                ('assembly', models.PositiveSmallIntegerField(choices=[(16, b'NCBI34/hg16'), (17, b'NCBI35/hg17'), (18, b'NCBI36/hg18'), (19, b'GRCh37/hg19'), (38, b'GRCh38/hg38')])),
                ('chrom', models.PositiveSmallIntegerField(verbose_name=b'Chromosome Location', choices=[(1, b'chr1'), (2, b'chr2'), (3, b'chr3'), (4, b'chr4'), (5, b'chr5'), (6, b'chr6'), (7, b'chr7'), (8, b'chr8'), (9, b'chr9'), (10, b'chr10'), (11, b'chr11'), (12, b'chr12'), (13, b'chr13'), (14, b'chr14'), (15, b'chr15'), (16, b'chr16'), (17, b'chr17'), (18, b'chr18'), (19, b'chr19'), (20, b'chr20'), (21, b'chr21'), (22, b'chr22'), (23, b'chrX'), (24, b'chrY'), (25, b'chrM'), (26, b'Other')])),
                ('strand', models.BooleanField(verbose_name=b'On the positive strand')),
                ('start_tx', models.PositiveIntegerField()),
                ('end_tx', models.PositiveIntegerField()),
                ('start_cds', models.PositiveIntegerField()),
                ('end_cds', models.PositiveIntegerField()),
                ('exon_count', models.PositiveIntegerField()),
                ('exon_starts', models.CommaSeparatedIntegerField(max_length=500)),
                ('exon_ends', models.CommaSeparatedIntegerField(max_length=500)),
                ('uniprot_display_id', models.CharField(max_length=100)),
                ('align_id', models.CharField(max_length=255)),
                ('has_gene_review', models.BooleanField(default=False)),
                ('gene_review_URLs', models.TextField(null=True, blank=True)),
                ('tile_end_cds', models.ForeignKey(related_name=b'gene_end_cds', to='tile_library.Tile')),
                ('tile_end_tx', models.ForeignKey(related_name=b'gene_end_tx', to='tile_library.Tile')),
                ('tile_start_cds', models.ForeignKey(related_name=b'gene_start_cds', to='tile_library.Tile')),
                ('tile_start_tx', models.ForeignKey(related_name=b'gene_start_tx', to='tile_library.Tile')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='genexref',
            name='gene',
            field=models.OneToOneField(related_name=b'x_ref', to='genes.UCSC_Gene'),
            preserve_default=True,
        ),
    ]
