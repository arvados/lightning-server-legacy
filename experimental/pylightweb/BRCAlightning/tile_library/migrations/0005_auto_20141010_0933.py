# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0004_genomestatistic'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomestatistic',
            name='avg_length',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='avg_variant_val',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='max_length',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='max_variant_val',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='min_length',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='statistics_type',
            field=models.PositiveSmallIntegerField(db_index=True),
        ),
    ]
