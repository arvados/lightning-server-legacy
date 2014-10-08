# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('genes', '0002_auto_20141006_0858'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ucsc_gene',
            name='gene_review_URLs',
        ),
        migrations.RemoveField(
            model_name='ucsc_gene',
            name='has_gene_review',
        ),
        migrations.AddField(
            model_name='genexref',
            name='gene_review_URLs',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='genexref',
            name='has_gene_review',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
