# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0020_auto_20141107_2040'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tilevariant',
            name='tile',
            field=models.ForeignKey(related_name=b'tile_variants', to='tile_library.Tile'),
        ),
    ]
