# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0021_auto_20141110_1327'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomevariant',
            name='end_tile_position',
            field=models.BigIntegerField(db_index=True),
        ),
        migrations.AlterField(
            model_name='genomevariant',
            name='start_tile_position',
            field=models.BigIntegerField(db_index=True),
        ),
    ]
