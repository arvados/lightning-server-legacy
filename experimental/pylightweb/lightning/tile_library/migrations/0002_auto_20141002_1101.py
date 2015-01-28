# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tilelocusannotation',
            options={'ordering': ['tile']},
        ),
        migrations.AlterModelOptions(
            name='tilevariant',
            options={'ordering': ['tile_variant_name']},
        ),
        migrations.AlterModelOptions(
            name='varannotation',
            options={'ordering': ['tile_variant']},
        ),
    ]
