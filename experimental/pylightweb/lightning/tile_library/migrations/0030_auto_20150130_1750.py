# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tile_library.models


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0029_auto_20150129_1416'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tile',
            name='end_tag',
            field=models.CharField(max_length=24, validators=[tile_library.models.validate_tag]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tile',
            name='start_tag',
            field=models.CharField(max_length=24, validators=[tile_library.models.validate_tag]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tile',
            name='tilename',
            field=models.BigIntegerField(db_index=True, serialize=False, editable=False, primary_key=True, validators=[tile_library.models.validate_tile_position_int]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='tile_variant_name',
            field=models.BigIntegerField(db_index=True, serialize=False, editable=False, primary_key=True, validators=[tile_library.models.validate_tile_variant_int]),
            preserve_default=True,
        ),
    ]
