# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0032_auto_20150202_1227'),
    ]

    operations = [
        migrations.RenameField(
            model_name='genomestatistic',
            old_name='position_num',
            new_name='num_of_positions',
        ),
        migrations.RenameField(
            model_name='genomestatistic',
            old_name='tile_num',
            new_name='num_of_tiles',
        ),
    ]
