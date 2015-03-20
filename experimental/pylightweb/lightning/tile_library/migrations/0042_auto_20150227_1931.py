# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0041_auto_20150224_1826'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='genomevariant',
            unique_together=set([('assembly_int', 'chromosome_int', 'alternate_chromosome_name', 'locus_start_int', 'locus_end_int', 'alternate_bases')]),
        ),
        migrations.AlterUniqueTogether(
            name='tilevariant',
            unique_together=set([('tile', 'md5sum')]),
        ),
    ]
