# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tile_library.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0045_auto_20150304_1716'),
    ]

    operations = [
        migrations.AddField(
            model_name='tile',
            name='is_end_of_path',
            field=models.BooleanField(default=False, editable=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='tile',
            name='is_start_of_path',
            field=models.BooleanField(default=False, editable=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='end_tag',
            field=models.CharField(default=b'', max_length=24, blank=True, validators=[tile_library.models.validate_tag]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='sequence',
            field=models.TextField(validators=[django.core.validators.RegexValidator(regex=b'[acgtn]+', message=b'Not a valid sequence, must be lowercase, and can only include a,c,g,t, or n.')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='start_tag',
            field=models.CharField(default=b'', max_length=24, blank=True, validators=[tile_library.models.validate_tag]),
            preserve_default=True,
        ),
    ]
