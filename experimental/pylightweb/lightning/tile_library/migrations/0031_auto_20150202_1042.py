# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0030_auto_20150130_1750'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tilevariant',
            name='conversion_to_cgf',
            field=models.TextField(default=b'', blank=True),
            preserve_default=True,
        ),
    ]
