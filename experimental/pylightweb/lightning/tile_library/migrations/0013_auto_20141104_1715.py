# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0012_auto_20141103_1548'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='genomevariant',
            name='tile_variants',
        ),
        migrations.DeleteModel(
            name='GenomeVariant',
        ),
    ]
