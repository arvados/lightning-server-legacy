# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tile_library.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0009_auto_20141020_1808'),
    ]

    operations = [
        migrations.CreateModel(
            name='GenomeVariant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tile_position', models.BigIntegerField()),
                ('names', models.TextField(help_text=b'Tab-separated aliases for this variant (rsID tags, RefSNP id, etc.', validators=[django.core.validators.RegexValidator(regex=b'[[\\S ]+\t]*', message=b'Not tab-separated')])),
                ('start', models.PositiveIntegerField(help_text=b'Positive integer, zero-indexed, relative to start of tile')),
                ('end', models.PositiveIntegerField(help_text=b'Positive integer, zero-indexed, relative to start of tile')),
                ('reference_bases', models.TextField(help_text=b"Text of variant bases, follows the regex pattern: [ACGT-]+\n'-' indicates an insertion", validators=[django.core.validators.RegexValidator(regex=b'[ACGT-]+', message=b'Not a valid sequence')])),
                ('alternate_bases', models.TextField(help_text=b"Text of variant bases, follows the regex pattern: [ACGT-]+\n'-' indicates a deletion", validators=[django.core.validators.RegexValidator(regex=b'[ACGT-]+', message=b'Not a valid sequence')])),
                ('info', models.TextField(help_text=b"Json-formatted. Known keys are 'source': [what generated the variant], and 'phenotype': [phenotypes associated with this annotation]", validators=[tile_library.models.validate_json])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('tile_variants', models.ManyToManyField(related_name=b'genome_variants', to='tile_library.TileVariant', db_index=True)),
            ],
            options={
                'ordering': ['tile_position'],
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='genomestatistic',
            name='statistics_type',
            field=models.PositiveSmallIntegerField(db_index=True, choices=[(0, b'Entire Genome'), (1, b'chr1'), (2, b'chr2'), (3, b'chr3'), (4, b'chr4'), (5, b'chr5'), (6, b'chr6'), (7, b'chr7'), (8, b'chr8'), (9, b'chr9'), (10, b'chr10'), (11, b'chr11'), (12, b'chr12'), (13, b'chr13'), (14, b'chr14'), (15, b'chr15'), (16, b'chr16'), (17, b'chr17'), (18, b'chr18'), (19, b'chr19'), (20, b'chr20'), (21, b'chr21'), (22, b'chr22'), (23, b'chrX'), (24, b'chrY'), (25, b'chrM'), (26, b'Other Chromosomes'), (27, b'Path')]),
        ),
    ]
