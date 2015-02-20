# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0037_auto_20150202_1749'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='genomevariant',
            options={'ordering': ['chromosome_int', 'alternate_chromosome_name', 'locus_start_int']},
        ),
        migrations.AlterModelOptions(
            name='tile',
            options={'ordering': ['tile_position_int']},
        ),
        migrations.AlterModelOptions(
            name='tilelocusannotation',
            options={'ordering': ['tile_position']},
        ),
        migrations.AlterModelOptions(
            name='tilevariant',
            options={'ordering': ['tile_variant_int']},
        ),
        migrations.RenameField(
            model_name='tile',
            old_name='tilename',
            new_name='tile_position_int',
        ),
        migrations.RenameField(
            model_name='tilelocusannotation',
            old_name='chromosome_name',
            new_name='alternate_chromosome_name',
        ),
        migrations.RenameField(
            model_name='tilelocusannotation',
            old_name='assembly',
            new_name='assembly_int',
        ),
        migrations.RenameField(
            model_name='tilelocusannotation',
            old_name='chromosome',
            new_name='chromosome_int',
        ),
        migrations.RenameField(
            model_name='tilelocusannotation',
            old_name='begin_int',
            new_name='start_int',
        ),
        migrations.RenameField(
            model_name='tilelocusannotation',
            old_name='tile',
            new_name='tile_position',
        ),
        migrations.RenameField(
            model_name='tilevariant',
            old_name='tile_variant_name',
            new_name='tile_variant_int',
        ),
        migrations.RemoveField(
            model_name='genomevariant',
            name='end_increment',
        ),
        migrations.RemoveField(
            model_name='genomevariant',
            name='end_tile_position',
        ),
        migrations.RemoveField(
            model_name='genomevariant',
            name='start_increment',
        ),
        migrations.RemoveField(
            model_name='genomevariant',
            name='start_tile_position',
        ),
        migrations.RemoveField(
            model_name='tilevariant',
            name='conversion_to_cgf',
        ),
        migrations.AddField(
            model_name='genomevariant',
            name='alternate_chromosome_name',
            field=models.CharField(default='', max_length=100, blank=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='genomevariant',
            name='assembly_int',
            field=models.PositiveSmallIntegerField(default=19, db_index=True, choices=[(16, b'NCBI34/hg16'), (17, b'NCBI35/hg17'), (18, b'NCBI36/hg18'), (19, b'GRCh37/hg19'), (38, b'GRCh38/hg38')]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='genomevariant',
            name='chromosome_int',
            field=models.PositiveSmallIntegerField(default=1, db_index=True, choices=[(1, b'chr1'), (2, b'chr2'), (3, b'chr3'), (4, b'chr4'), (5, b'chr5'), (6, b'chr6'), (7, b'chr7'), (8, b'chr8'), (9, b'chr9'), (10, b'chr10'), (11, b'chr11'), (12, b'chr12'), (13, b'chr13'), (14, b'chr14'), (15, b'chr15'), (16, b'chr16'), (17, b'chr17'), (18, b'chr18'), (19, b'chr19'), (20, b'chr20'), (21, b'chr21'), (22, b'chr22'), (23, b'chrX'), (24, b'chrY'), (25, b'chrM'), (26, b'Other')]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='genomevariant',
            name='locus_end_int',
            field=models.PositiveIntegerField(default=1, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='genomevariant',
            name='locus_start_int',
            field=models.PositiveIntegerField(default=0, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tilelocusannotation',
            name='tile_variant_value',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='genomevarianttranslation',
            name='genome_variant',
            field=models.ForeignKey(related_name='translation_to_tile_variant', to='tile_library.GenomeVariant'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='genomevariant',
            unique_together=set([('assembly_int', 'chromosome_int', 'alternate_chromosome_name', 'locus_start_int', 'alternate_bases')]),
        ),
        migrations.AlterUniqueTogether(
            name='tilelocusannotation',
            unique_together=set([('tile_position', 'assembly_int')]),
        ),
    ]
