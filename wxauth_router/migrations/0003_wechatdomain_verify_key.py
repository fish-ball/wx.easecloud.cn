# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-10-19 02:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wxauth_router', '0002_auto_20160920_0528'),
    ]

    operations = [
        migrations.AddField(
            model_name='wechatdomain',
            name='verify_key',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='认证文件编码'),
        ),
    ]
