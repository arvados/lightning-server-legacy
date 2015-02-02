# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0033_auto_20150202_1339'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomestatistic',
            name='max_num_positions_spanned',
            field=models.PositiveIntegerField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
