# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tile_library.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0015_auto_20141104_1726'),
    ]

    operations = [
        migrations.CreateModel(
            name='GenomeVariant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tile_position', models.BigIntegerField()),
                ('names', models.TextField(help_text=b'Tab-separated aliases for this variant (rsID tags, RefSNP id, etc.', blank=True)),
                ('reference_bases', models.TextField(help_text=b"Text of variant bases, follows the regex pattern: [ACGT-]+\n'-' indicates an insertion", validators=[django.core.validators.RegexValidator(regex=b'[ACGT-]+', message=b'Not a valid sequence')])),
                ('alternate_bases', models.TextField(help_text=b"Text of variant bases, follows the regex pattern: [ACGT-]+\n'-' indicates a deletion", validators=[django.core.validators.RegexValidator(regex=b'[ACGT-]+', message=b'Not a valid sequence')])),
                ('info', models.TextField(help_text=b"Json-formatted. Known keys are 'source': [what generated the variant], and 'phenotype': [phenotypes associated with this annotation]", validators=[tile_library.models.validate_json])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['tile_position'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GenomeVariantTranslation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start', models.PositiveIntegerField(help_text=b'Positive integer, zero-indexed, relative to start of that tilevariant')),
                ('end', models.PositiveIntegerField(help_text=b'Positive integer, zero-indexed, relative to start of that tilevariant. Exclusive')),
                ('genome_variant', models.ForeignKey(to='tile_library.GenomeVariant')),
                ('tile_variant', models.ForeignKey(to='tile_library.TileVariant')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='genomevariant',
            name='tile_variants',
            field=models.ManyToManyField(related_name=b'genome_variants', through='tile_library.GenomeVariantTranslation', to='tile_library.TileVariant', db_index=True),
            preserve_default=True,
        ),
    ]
