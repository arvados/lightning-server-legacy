# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tile_library.models


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0035_auto_20150202_1616'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomestatistic',
            name='path_name',
            field=models.IntegerField(default=-1, db_index=True),
            preserve_default=True,
        ),
    ]
