# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0011_auto_20141103_1546'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomevariant',
            name='names',
            field=models.TextField(help_text=b'Tab-separated aliases for this variant (rsID tags, RefSNP id, etc.', blank=True),
        ),
    ]
