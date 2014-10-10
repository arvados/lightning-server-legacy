# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0005_auto_20141010_0933'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomestatistic',
            name='avg_annotations_per_position',
            field=models.DecimalField(null=True, max_digits=15, decimal_places=3, blank=True),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='avg_annotations_per_tile',
            field=models.DecimalField(null=True, max_digits=15, decimal_places=3, blank=True),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='avg_length',
            field=models.DecimalField(null=True, max_digits=15, decimal_places=3),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='avg_variant_val',
            field=models.DecimalField(null=True, max_digits=15, decimal_places=3),
        ),
    ]
