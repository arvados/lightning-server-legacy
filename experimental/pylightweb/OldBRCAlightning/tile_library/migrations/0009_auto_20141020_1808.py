# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0008_auto_20141017_1402'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='genomestatistic',
            unique_together=set([('statistics_type', 'path_name')]),
        ),
    ]
