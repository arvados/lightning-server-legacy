# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0006_auto_20141010_1100'),
    ]

    operations = [
        migrations.AddField(
            model_name='genomestatistic',
            name='path_name',
            field=models.PositiveIntegerField(db_index=True, null=True, blank=True),
            preserve_default=True,
        ),
    ]
