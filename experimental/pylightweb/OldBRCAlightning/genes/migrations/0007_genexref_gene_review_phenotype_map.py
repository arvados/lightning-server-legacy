# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('genes', '0006_auto_20141007_1112'),
    ]

    operations = [
        migrations.AddField(
            model_name='genexref',
            name='gene_review_phenotype_map',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
