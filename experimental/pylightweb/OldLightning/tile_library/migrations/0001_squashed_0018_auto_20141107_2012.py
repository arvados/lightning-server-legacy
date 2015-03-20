# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    replaces = [(b'tile_library', '0001_initial'), (b'tile_library', '0002_auto_20141002_1101'), (b'tile_library', '0003_auto_20141009_1345'), (b'tile_library', '0004_genomestatistic'), (b'tile_library', '0005_auto_20141010_0933'), (b'tile_library', '0006_auto_20141010_1100'), (b'tile_library', '0007_genomestatistic_path_name'), (b'tile_library', '0008_auto_20141017_1402'), (b'tile_library', '0009_auto_20141020_1808'), (b'tile_library', '0010_auto_20141103_1533'), (b'tile_library', '0011_auto_20141103_1546'), (b'tile_library', '0012_auto_20141103_1548'), (b'tile_library', '0013_auto_20141104_1715'), (b'tile_library', '0014_auto_20141104_1716'), (b'tile_library', '0015_auto_20141104_1726'), (b'tile_library', '0016_auto_20141104_1727'), (b'tile_library', '0017_auto_20141106_1306'), (b'tile_library', '0018_auto_20141107_2012')]

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
        migrations.AlterModelOptions(
            name='tilelocusannotation',
            options={'ordering': ['tile']},
        ),
        migrations.AlterModelOptions(
            name='tilevariant',
            options={'ordering': ['tile_variant_name']},
        ),
        migrations.AlterModelOptions(
            name='varannotation',
            options={'ordering': ['tile_variant']},
        ),
        migrations.AlterField(
            model_name='tile',
            name='tilename',
            field=models.BigIntegerField(serialize=False, editable=False, primary_key=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='tilelocusannotation',
            name='assembly',
            field=models.PositiveSmallIntegerField(db_index=True, choices=[(16, b'NCBI34/hg16'), (17, b'NCBI35/hg17'), (18, b'NCBI36/hg18'), (19, b'GRCh37/hg19'), (38, b'GRCh38/hg38')]),
        ),
        migrations.AlterField(
            model_name='tilelocusannotation',
            name='begin_int',
            field=models.PositiveIntegerField(db_index=True),
        ),
        migrations.AlterField(
            model_name='tilelocusannotation',
            name='chromosome',
            field=models.PositiveSmallIntegerField(db_index=True, choices=[(1, b'chr1'), (2, b'chr2'), (3, b'chr3'), (4, b'chr4'), (5, b'chr5'), (6, b'chr6'), (7, b'chr7'), (8, b'chr8'), (9, b'chr9'), (10, b'chr10'), (11, b'chr11'), (12, b'chr12'), (13, b'chr13'), (14, b'chr14'), (15, b'chr15'), (16, b'chr16'), (17, b'chr17'), (18, b'chr18'), (19, b'chr19'), (20, b'chr20'), (21, b'chr21'), (22, b'chr22'), (23, b'chrX'), (24, b'chrY'), (25, b'chrM'), (26, b'Other')]),
        ),
        migrations.AlterField(
            model_name='tilelocusannotation',
            name='end_int',
            field=models.PositiveIntegerField(db_index=True),
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='length',
            field=models.PositiveIntegerField(db_index=True),
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='tile_variant_name',
            field=models.BigIntegerField(serialize=False, editable=False, primary_key=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='variant_value',
            field=models.PositiveIntegerField(db_index=True),
        ),
        migrations.CreateModel(
            name='GenomeStatistic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('statistics_type', models.PositiveSmallIntegerField(db_index=True)),
                ('position_num', models.BigIntegerField()),
                ('tile_num', models.BigIntegerField()),
                ('avg_variant_val', models.DecimalField(null=True, max_digits=15, decimal_places=3)),
                ('max_variant_val', models.PositiveIntegerField(null=True)),
                ('min_length', models.PositiveIntegerField(null=True)),
                ('avg_length', models.DecimalField(null=True, max_digits=15, decimal_places=3)),
                ('max_length', models.PositiveIntegerField(null=True)),
                ('avg_annotations_per_position', models.DecimalField(null=True, max_digits=15, decimal_places=3, blank=True)),
                ('max_annotations_per_position', models.PositiveIntegerField(null=True, blank=True)),
                ('avg_annotations_per_tile', models.DecimalField(null=True, max_digits=15, decimal_places=3, blank=True)),
                ('max_annotations_per_tile', models.PositiveIntegerField(null=True, blank=True)),
                ('path_name', models.PositiveIntegerField(db_index=True, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='tilelocusannotation',
            unique_together=set([('tile', 'assembly')]),
        ),
        migrations.AlterUniqueTogether(
            name='genomestatistic',
            unique_together=set([('statistics_type', 'path_name')]),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='statistics_type',
            field=models.PositiveSmallIntegerField(db_index=True, choices=[(0, b'Entire Genome'), (1, b'chr1'), (2, b'chr2'), (3, b'chr3'), (4, b'chr4'), (5, b'chr5'), (6, b'chr6'), (7, b'chr7'), (8, b'chr8'), (9, b'chr9'), (10, b'chr10'), (11, b'chr11'), (12, b'chr12'), (13, b'chr13'), (14, b'chr14'), (15, b'chr15'), (16, b'chr16'), (17, b'chr17'), (18, b'chr18'), (19, b'chr19'), (20, b'chr20'), (21, b'chr21'), (22, b'chr22'), (23, b'chrX'), (24, b'chrY'), (25, b'chrM'), (26, b'Other Chromosomes'), (27, b'Path')]),
        ),
    ]
