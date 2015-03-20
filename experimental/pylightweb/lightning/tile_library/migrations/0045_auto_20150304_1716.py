# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0044_auto_20150304_1415'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='lanterntranslator',
            options={'ordering': ['lantern_name']},
        ),
        migrations.AlterField(
            model_name='lanterntranslator',
            name='lantern_name',
            field=models.TextField(unique=True, validators=[django.core.validators.RegexValidator(regex=b'^([0-9a-f]{3}\\.[0-9a-f]{2}\\.[0-9a-f]{4})\\.[0-9a-f]{4}(?:\\+([0-9a-f]+)$|$)', message=b'Not a valid lantern name format (specified in tile_library.constants.LANTERN_NAME_FORMAT_STRING)')]),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='lanterntranslator',
            unique_together=set([('tile_variant_int', 'tile_library_host')]),
        ),
    ]
