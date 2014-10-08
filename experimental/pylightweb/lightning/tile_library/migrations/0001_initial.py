# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Tile',
            fields=[
                ('tilename', models.BigIntegerField(serialize=False, editable=False, primary_key=True)),
                ('start_tag', models.CharField(max_length=24)),
                ('end_tag', models.CharField(max_length=24)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['tilename'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TileLocusAnnotation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('assembly', models.PositiveSmallIntegerField(choices=[(16, b'NCBI34/hg16'), (17, b'NCBI35/hg17'), (18, b'NCBI36/hg18'), (19, b'GRCh37/hg19'), (38, b'GRCh38/hg38')])),
                ('chromosome', models.PositiveSmallIntegerField(choices=[(1, b'chr1'), (2, b'chr2'), (3, b'chr3'), (4, b'chr4'), (5, b'chr5'), (6, b'chr6'), (7, b'chr7'), (8, b'chr8'), (9, b'chr9'), (10, b'chr10'), (11, b'chr11'), (12, b'chr12'), (13, b'chr13'), (14, b'chr14'), (15, b'chr15'), (16, b'chr16'), (17, b'chr17'), (18, b'chr18'), (19, b'chr19'), (20, b'chr20'), (21, b'chr21'), (22, b'chr22'), (23, b'chrX'), (24, b'chrY'), (25, b'chrM'), (26, b'Other')])),
                ('begin_int', models.PositiveIntegerField()),
                ('end_int', models.PositiveIntegerField()),
                ('chromosome_name', models.CharField(max_length=100)),
                ('tile', models.ForeignKey(related_name=b'tile_locus_annotations', to='tile_library.Tile')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TileVariant',
            fields=[
                ('tile_variant_name', models.BigIntegerField(serialize=False, editable=False, primary_key=True)),
                ('variant_value', models.PositiveIntegerField()),
                ('length', models.PositiveIntegerField()),
                ('md5sum', models.CharField(max_length=40)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('sequence', models.TextField()),
                ('start_tag', models.TextField(blank=True)),
                ('end_tag', models.TextField(blank=True)),
                ('tile', models.ForeignKey(related_name=b'variants', to='tile_library.Tile')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VarAnnotation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('annotation_type', models.CharField(max_length=10, choices=[(b'SNP_INDEL', b'SNP or Insert/Deletion Annotation'), (b'DATABASE', b'Database Annotation'), (b'PHEN', b'Phenotype Annotation not associated with a SNP or INDEL or database annotation'), (b'OTHER', b'Other type of Annotation')])),
                ('source', models.CharField(max_length=100)),
                ('annotation_text', models.TextField()),
                ('phenotype', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('tile_variant', models.ForeignKey(related_name=b'annotations', to='tile_library.TileVariant')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
