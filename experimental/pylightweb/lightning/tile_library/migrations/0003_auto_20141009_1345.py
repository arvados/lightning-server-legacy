# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0002_auto_20141002_1101'),
    ]

    operations = [
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
    ]
