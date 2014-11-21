# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('genes', '0004_auto_20141006_1509'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ucsc_gene',
            name='tile_end_cds',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='ucsc_gene',
            name='tile_end_tx',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='ucsc_gene',
            name='tile_start_cds',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='ucsc_gene',
            name='tile_start_tx',
            field=models.BigIntegerField(),
        ),
    ]
