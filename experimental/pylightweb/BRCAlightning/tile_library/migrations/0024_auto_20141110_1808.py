# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0023_auto_20141110_1807'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomevariant',
            name='start_tile_position',
            field=models.ForeignKey(related_name=b'genome_variants', to='tile_library.Tile'),
        ),
    ]
