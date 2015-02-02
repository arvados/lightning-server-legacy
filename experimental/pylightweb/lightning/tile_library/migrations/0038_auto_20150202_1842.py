# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0037_auto_20150202_1749'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='genomevariant',
            unique_together=set([('start_tile_position', 'end_increment', 'alternate_bases')]),
        ),
    ]
