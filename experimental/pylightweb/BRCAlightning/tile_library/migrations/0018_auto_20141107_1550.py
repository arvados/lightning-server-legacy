# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0017_auto_20141106_1306'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='varannotation',
            name='tile_variant',
        ),
        migrations.DeleteModel(
            name='VarAnnotation',
        ),
        migrations.AlterModelOptions(
            name='genomevariant',
            options={'ordering': ['start_tile_position']},
        ),
        migrations.RenameField(
            model_name='genomevariant',
            old_name='tile_position',
            new_name='start_tile_position',
        ),
        migrations.AddField(
            model_name='genomestatistic',
            name='avg_num_positions_spanned',
            field=models.DecimalField(null=True, max_digits=15, decimal_places=3),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='genomestatistic',
            name='max_num_positions_spanned',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='genomevariant',
            name='end_increment',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='genomevariant',
            name='end_tile_position',
            field=models.BigIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='genomevariant',
            name='start_increment',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tilevariant',
            name='num_positions_spanned',
            field=models.PositiveSmallIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='avg_annotations_per_position',
            field=models.DecimalField(null=True, max_digits=15, decimal_places=3),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='avg_annotations_per_tile',
            field=models.DecimalField(null=True, max_digits=15, decimal_places=3),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='max_annotations_per_position',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='max_annotations_per_tile',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='genomevarianttranslation',
            name='genome_variant',
            field=models.ForeignKey(related_name=b'translation_to_tile', to='tile_library.GenomeVariant'),
        ),
        migrations.AlterField(
            model_name='genomevarianttranslation',
            name='tile_variant',
            field=models.ForeignKey(related_name=b'translation_to_genome_variant', to='tile_library.TileVariant'),
        ),
    ]
