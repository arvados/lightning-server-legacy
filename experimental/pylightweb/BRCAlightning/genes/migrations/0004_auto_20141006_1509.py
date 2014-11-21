# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('genes', '0003_auto_20141006_1055'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ucsc_gene',
            name='exon_ends',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='ucsc_gene',
            name='exon_starts',
            field=models.TextField(),
        ),
    ]
