# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0026_auto_20141110_1923'),
    ]

    operations = [
        migrations.AddField(
            model_name='tilevariant',
            name='conversion_to_cgf',
            field=models.TextField(default=b''),
            preserve_default=True,
        ),
    ]
