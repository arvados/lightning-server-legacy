# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0007_genomestatistic_path_name'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='tilelocusannotation',
            unique_together=set([('tile', 'assembly')]),
        ),
    ]
