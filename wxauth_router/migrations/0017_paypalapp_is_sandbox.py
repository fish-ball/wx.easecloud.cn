# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-03-13 14:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wxauth_router', '0016_paypalapp'),
    ]

    operations = [
        migrations.AddField(
            model_name='paypalapp',
            name='is_sandbox',
            field=models.BooleanField(default=False, verbose_name='是否沙盒测试环境'),
        ),
    ]