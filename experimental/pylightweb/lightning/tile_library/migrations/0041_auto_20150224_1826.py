# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0040_auto_20150223_1333'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomevariant',
            name='names',
            field=models.TextField(help_text=b'Tab-separated aliases for this variant (rsID tags, RefSNP id, etc.', db_index=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='genomevarianttranslation',
            name='genome_variant',
            field=models.ForeignKey(related_name='translations_to_tile_variant', to='tile_library.GenomeVariant'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='genomevarianttranslation',
            name='tile_variant',
            field=models.ForeignKey(related_name='translations_to_genome_variant', to='tile_library.TileVariant'),
            preserve_default=True,
        ),
    ]
