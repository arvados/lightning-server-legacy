# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0028_auto_20141210_1126'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='genomestatistic',
            name='avg_annotations_per_position',
        ),
        migrations.RemoveField(
            model_name='genomestatistic',
            name='avg_annotations_per_tile',
        ),
        migrations.RemoveField(
            model_name='genomestatistic',
            name='avg_length',
        ),
        migrations.RemoveField(
            model_name='genomestatistic',
            name='avg_num_positions_spanned',
        ),
        migrations.RemoveField(
            model_name='genomestatistic',
            name='avg_variant_val',
        ),
        migrations.RemoveField(
            model_name='genomestatistic',
            name='max_annotations_per_position',
        ),
        migrations.RemoveField(
            model_name='genomestatistic',
            name='max_annotations_per_tile',
        ),
        migrations.RemoveField(
            model_name='genomestatistic',
            name='max_length',
        ),
        migrations.RemoveField(
            model_name='genomestatistic',
            name='max_variant_val',
        ),
        migrations.RemoveField(
            model_name='genomestatistic',
            name='min_length',
        ),
    ]
