# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-03-13 18:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wxauth_router', '0019_auto_20170313_1435'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alipayapp',
            name='oauth_redirect_url',
            field=models.URLField(blank=True, default='', help_text='如果是，请务必将本地址设定为本 API 的 index，例如 http://wx.easecloud.cn并且在对应的平台中注册此地址，不填的话默认会使用当前地址', verbose_name='OAuth 认证跳转地址'),
        ),
        migrations.AlterField(
            model_name='alipaymapiapp',
            name='oauth_redirect_url',
            field=models.URLField(blank=True, default='', help_text='如果是，请务必将本地址设定为本 API 的 index，例如 http://wx.easecloud.cn并且在对应的平台中注册此地址，不填的话默认会使用当前地址', verbose_name='OAuth 认证跳转地址'),
        ),
        migrations.AlterField(
            model_name='paypalapp',
            name='oauth_redirect_url',
            field=models.URLField(blank=True, default='', help_text='如果是，请务必将本地址设定为本 API 的 index，例如 http://wx.easecloud.cn并且在对应的平台中注册此地址，不填的话默认会使用当前地址', verbose_name='OAuth 认证跳转地址'),
        ),
        migrations.AlterField(
            model_name='wechatapp',
            name='oauth_redirect_url',
            field=models.URLField(blank=True, default='', help_text='如果是，请务必将本地址设定为本 API 的 index，例如 http://wx.easecloud.cn并且在对应的平台中注册此地址，不填的话默认会使用当前地址', verbose_name='OAuth 认证跳转地址'),
        ),
    ]
