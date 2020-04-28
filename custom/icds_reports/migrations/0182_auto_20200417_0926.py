# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2020-04-17 09:26
from __future__ import unicode_literals

from django.db import migrations, models
from custom.icds_reports.const import BIHAR_API_DEMOGRAPHICS_TABLE
from custom.icds_reports.utils.migrations import get_view_migrations


class Migration(migrations.Migration):

    dependencies = [
        ('icds_reports', '0181_auto_20200418_0946'),
    ]

    operations = [
        migrations.AddField(
            model_name='biharapidemographics',
            name='last_class_attended_ever',
            field=models.SmallIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='biharapidemographics',
            name='out_of_school_status',
            field=models.SmallIntegerField(null=True),
        ),
        migrations.RunSQL(f"CREATE INDEX idx_demographics_gender_dob ON {BIHAR_API_DEMOGRAPHICS_TABLE} (gender, dob)")
    ]
