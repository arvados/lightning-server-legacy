# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('genes', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ucsc_gene',
            name='strand',
            field=models.NullBooleanField(verbose_name=b'On the positive strand'),
        ),
    ]
