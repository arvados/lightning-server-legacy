# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0043_auto_20150304_1149'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lanterntranslator',
            name='tile_library_access_point',
        ),
        migrations.AddField(
            model_name='lanterntranslator',
            name='tile_library_host',
            field=models.TextField(default=b'', blank=True),
            preserve_default=True,
        ),
    ]
