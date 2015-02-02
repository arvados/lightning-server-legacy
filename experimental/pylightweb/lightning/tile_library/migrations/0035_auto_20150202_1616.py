# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tile_library.models


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0034_auto_20150202_1349'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomestatistic',
            name='max_num_positions_spanned',
            field=models.PositiveIntegerField(blank=True, null=True, validators=[tile_library.models.validate_num_spanning_tiles]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='num_of_positions',
            field=models.BigIntegerField(validators=[tile_library.models.validate_positive]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='num_of_tiles',
            field=models.BigIntegerField(validators=[tile_library.models.validate_positive]),
            preserve_default=True,
        ),
    ]
