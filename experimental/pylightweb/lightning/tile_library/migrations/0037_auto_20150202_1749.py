# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0036_auto_20150202_1653'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tilelocusannotation',
            name='chromosome_name',
            field=models.CharField(max_length=100, blank=True),
            preserve_default=True,
        ),
    ]
