# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tile_library.models


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0027_tilevariant_conversion_to_cgf'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomevariant',
            name='info',
            field=models.TextField(help_text=b"Json-formatted. Known keys are 'source': [what generated the variant],                   'phenotype': [phenotypes associated with this annotation], 'amino_acid': [predicted amino-acid changes],                   'ucsc_trans': [UCSC translation (picked up from GFF files), and 'other': [Other GFF-file related annotations]", db_index=True, validators=[tile_library.models.validate_json]),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='genomevarianttranslation',
            unique_together=set([('tile_variant', 'genome_variant')]),
        ),
    ]
