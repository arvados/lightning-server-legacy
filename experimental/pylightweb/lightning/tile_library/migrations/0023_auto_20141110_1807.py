# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0022_auto_20141110_1750'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomevariant',
            name='start_tile_position',
            field=models.ForeignKey(to='tile_library.Tile'),
        ),
        migrations.AlterField(
            model_name='genomevarianttranslation',
            name='genome_variant',
            field=models.ForeignKey(related_name=b'translation_to_tilevariant', to='tile_library.GenomeVariant'),
        ),
    ]
