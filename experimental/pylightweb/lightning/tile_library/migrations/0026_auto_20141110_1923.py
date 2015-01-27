# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0025_auto_20141110_1815'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomevariant',
            name='end_tile_position',
            field=models.ForeignKey(related_name=b'ending_genome_variants', to='tile_library.Tile'),
        ),
        migrations.AlterField(
            model_name='genomevariant',
            name='start_tile_position',
            field=models.ForeignKey(related_name=b'starting_genome_variants', to='tile_library.Tile'),
        ),
    ]
