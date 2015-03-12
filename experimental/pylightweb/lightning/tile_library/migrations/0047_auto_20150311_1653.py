# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tile_library.models


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0046_auto_20150311_1637'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tile',
            name='end_tag',
            field=models.CharField(blank=True, max_length=24, validators=[tile_library.models.validate_tag]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tile',
            name='start_tag',
            field=models.CharField(blank=True, max_length=24, validators=[tile_library.models.validate_tag]),
            preserve_default=True,
        ),
    ]
