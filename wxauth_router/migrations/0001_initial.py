# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-29 15:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AuthLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(max_length=128, verbose_name='回传state')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='请求时间')),
            ],
            options={
                'verbose_name': '验证日志',
                'verbose_name_plural': '验证日志',
                'db_table': 'wxauth_authlog',
            },
        ),
        migrations.CreateModel(
            name='RequestTarget',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(unique=True, verbose_name='目标URL')),
                ('key', models.CharField(max_length=8, unique=True, verbose_name='目标')),
            ],
            options={
                'verbose_name': '请求目标',
                'verbose_name_plural': '请求目标',
                'db_table': 'wxauth_request_target',
            },
        ),
        migrations.CreateModel(
            name='WechatUser',
            fields=[
                ('openid', models.CharField(max_length=64, primary_key=True, serialize=False, verbose_name='用户OpenID')),
                ('nickname', models.CharField(default='', max_length=128, verbose_name='用户昵称')),
                ('sex', models.IntegerField(choices=[(0, '未知'), (1, '男'), (2, '女')], default=0, verbose_name='性别')),
                ('province', models.CharField(max_length=120, verbose_name='省份')),
                ('city', models.CharField(max_length=120, verbose_name='城市')),
                ('country', models.CharField(max_length=120, verbose_name='国家')),
                ('headimgurl', models.URLField(verbose_name='用户头像')),
                ('privilege', models.TextField(default='', verbose_name='用户特权信息')),
                ('unionid', models.CharField(max_length=64, null=True, verbose_name='用户unionid')),
            ],
            options={
                'verbose_name': '微信用户',
                'verbose_name_plural': '微信用户',
                'db_table': 'wxauth_wechat_user',
            },
        ),
        migrations.AddField(
            model_name='authlog',
            name='target',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='wxauth_router.RequestTarget', verbose_name='目标'),
        ),
    ]
