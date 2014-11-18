# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0018_auto_20141107_1550'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='genomevariant',
            options={'ordering': ['start_tile_position', 'start_increment']},
        ),
        migrations.AlterField(
            model_name='genomevariant',
            name='end_tile_position',
            field=models.ForeignKey(related_name=b'genome_variants_ending', to='tile_library.Tile'),
        ),
        migrations.AlterField(
            model_name='genomevariant',
            name='start_tile_position',
            field=models.ForeignKey(related_name=b'genome_variants_starting', to='tile_library.Tile'),
        ),
    ]
