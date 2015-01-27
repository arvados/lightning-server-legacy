# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tile_library', '0003_auto_20141009_1345'),
    ]

    operations = [
        migrations.CreateModel(
            name='GenomeStatistic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('statistics_type', models.PositiveSmallIntegerField()),
                ('position_num', models.BigIntegerField()),
                ('tile_num', models.BigIntegerField()),
                ('avg_variant_val', models.PositiveIntegerField()),
                ('max_variant_val', models.PositiveIntegerField()),
                ('min_length', models.PositiveIntegerField()),
                ('avg_length', models.PositiveIntegerField()),
                ('max_length', models.PositiveIntegerField()),
                ('avg_annotations_per_position', models.PositiveIntegerField(null=True, blank=True)),
                ('max_annotations_per_position', models.PositiveIntegerField(null=True, blank=True)),
                ('avg_annotations_per_tile', models.PositiveIntegerField(null=True, blank=True)),
                ('max_annotations_per_tile', models.PositiveIntegerField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
