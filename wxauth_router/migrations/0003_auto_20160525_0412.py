# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-25 04:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wxauth_router', '0002_auto_20160430_0217'),
    ]

    operations = [
        migrations.CreateModel(
            name='WechatDomain',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='可以填写公众号的显示名称', max_length=150, verbose_name='标题')),
                ('domain', models.CharField(help_text='公众号 > 开发 > 接口权限 > 网页授权获取用户基本信息', max_length=150, unique=True, verbose_name='域名')),
                ('app_id', models.CharField(max_length=50, unique=True, verbose_name='公众号 APP_ID')),
            ],
            options={
                'verbose_name_plural': '公众号域',
                'verbose_name': '公众号域',
                'db_table': 'wxauth_wechat_domain',
            },
        ),
        migrations.AddField(
            model_name='wechatuser',
            name='domain',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='wxauth_router.WechatDomain', verbose_name='公众号域'),
        ),
    ]