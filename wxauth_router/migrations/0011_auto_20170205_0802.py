# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-02-05 08:02
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wxauth_router', '0010_wechatapp_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wechatuser',
            name='domain',
        ),
        migrations.DeleteModel(
            name='WechatDomain',
        ),
    ]