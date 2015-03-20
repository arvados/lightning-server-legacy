# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0016_auto_20141104_1727'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genomevariant',
            name='id',
            field=models.BigIntegerField(serialize=False, editable=False, primary_key=True),
        ),
    ]
