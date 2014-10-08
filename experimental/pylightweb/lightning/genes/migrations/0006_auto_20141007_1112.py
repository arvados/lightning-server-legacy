# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('genes', '0005_auto_20141007_1028'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='genexref',
            options={'verbose_name': 'Gene database xref'},
        ),
        migrations.AlterModelOptions(
            name='ucsc_gene',
            options={'ordering': ['chrom', 'start_tx'], 'verbose_name': 'Known Gene: UCSC', 'verbose_name_plural': 'Known Genes: UCSC'},
        ),
    ]
