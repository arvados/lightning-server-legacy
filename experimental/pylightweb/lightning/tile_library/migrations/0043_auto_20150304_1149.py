# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tile_library.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0042_auto_20150227_1931'),
    ]

    operations = [
        migrations.CreateModel(
            name='LanternTranslator',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('lantern_name', models.TextField(validators=[django.core.validators.RegexValidator(regex=b'^([0-9a-f]{3}\\.[0-9a-f]{2}\\.[0-9a-f]{4})\\.[0-9a-f]{4}(?:\\+([0-9a-f]+)$|$)', message=b'Not a valid lantern name format (specified in tile_library.constants.LANTERN_NAME_FORMAT_STRING)')])),
                ('tile_library_access_point', models.TextField()),
                ('tile_variant_int', models.BigIntegerField(db_index=True, validators=[tile_library.models.validate_tile_variant_int])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='md5sum',
            field=models.CharField(max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tilevariant',
            name='sequence',
            field=models.TextField(validators=[django.core.validators.RegexValidator(regex=b'[ACGTN]+', message=b'Not a valid sequence, must be uppercase, and can only include A,C,G,T, or N.')]),
            preserve_default=True,
        ),
    ]
