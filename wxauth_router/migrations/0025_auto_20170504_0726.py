# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-05-04 07:26
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wxauth_router', '0024_wechatapp_parent'),
    ]

    operations = [
        migrations.CreateModel(
            name='WechatWithdrawTicket',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=32, verbose_name='令牌值')),
                ('expires', models.IntegerField(verbose_name='超时时间')),
                ('amount', models.IntegerField(help_text='单位：分', verbose_name='提现金额')),
                ('status', models.TextField(choices=[('PENDING', '申请中'), ('SUCCESS', '成功'), ('FAIL', '失败'), ('REJECTED', '驳回')], default='PENDING', verbose_name='提现状态')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='withdraw_tickets', to='wxauth_router.WechatUser', verbose_name='提现用户')),
            ],
            options={
                'verbose_name': '提现票据',
                'db_table': 'wxauth_wechat_withdraw_ticket',
            },
        ),
        migrations.RemoveField(
            model_name='wechatapp',
            name='parent',
        ),
        migrations.AlterModelTable(
            name='resultticket',
            table='wxauth_result_ticket',
        ),
    ]