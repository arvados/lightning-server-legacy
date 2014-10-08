# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Human',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('phaseA_npy', models.FileField(upload_to=b'numpy_abvs', verbose_name=b'Numpy-readable ABV file (Phase A or unphased)')),
                ('phaseB_npy', models.FileField(upload_to=b'numpy_abvs', null=True, verbose_name=b'Numpy-readable ABV file (Phase B)', blank=True)),
                ('index_in_big_file', models.PositiveIntegerField()),
                ('name', models.CharField(verbose_name=b'PGP id', max_length=8, null=True, editable=False, blank=True)),
                ('chromosomal_sex', models.CharField(max_length=10, choices=[(b'XX', b'XX'), (b'XY', b'XY'), (b'XX/XY', b'XX/XY'), (b'XXX', b'XXX'), (b'XXY', b'XXY'), (b'OTHER', b'Other'), (b'UNKNOWN', b'Unknown')])),
                ('gender', models.CharField(max_length=10, choices=[(b'MALE', b'Male'), (b'FEMALE', b'Female'), (b'TRANS', b'Trans*'), (b'OTHER', b'Other'), (b'UNKNOWN', b'Unknown')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('date_of_birth', models.DateTimeField(null=True, blank=True)),
                ('age_range', models.IntegerField(choices=[(-1, b'Unknown'), (0, b'0-9 years'), (10, b'10-19 years'), (20, b'20-29 years'), (30, b'30-39 years'), (40, b'40-49 years'), (50, b'50-59 years'), (60, b'60-69 years'), (70, b'70-79 years'), (80, b'80-89 years'), (90, b'90-99 years'), (100, b'100-109 years'), (110, b'110 years or up')])),
                ('ethnicity', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='IndividualGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('group_type', models.CharField(max_length=100)),
                ('info', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='human',
            name='groups',
            field=models.ManyToManyField(related_name=b'groupIds', null=True, to='humans.IndividualGroup', blank=True),
            preserve_default=True,
        ),
    ]
