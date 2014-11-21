# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0014_auto_20141104_1716'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='genomevariant',
            name='tile_variants',
        ),
        migrations.RemoveField(
            model_name='translation',
            name='genome_variant',
        ),
        migrations.DeleteModel(
            name='GenomeVariant',
        ),
        migrations.RemoveField(
            model_name='translation',
            name='tile_variant',
        ),
        migrations.DeleteModel(
            name='Translation',
        ),
    ]
