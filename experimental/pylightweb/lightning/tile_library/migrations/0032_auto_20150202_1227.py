# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tile_library.models


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0031_auto_20150202_1042'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tilevariant',
            name='end_tag',
            field=models.CharField(default=b'', max_length=24, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='num_positions_spanned',
            field=models.PositiveSmallIntegerField(validators=[tile_library.models.validate_num_spanning_tiles]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='start_tag',
            field=models.CharField(default=b'', max_length=24, blank=True),
            preserve_default=True,
        ),
    ]
