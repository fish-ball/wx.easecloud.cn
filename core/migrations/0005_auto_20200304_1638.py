# Generated by Django 3.0.2 on 2020-03-04 16:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_wechatapp_template_send_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wechatapp',
            name='api_key',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='API 密钥'),
        ),
        migrations.AlterField(
            model_name='wechatapp',
            name='mch_id',
            field=models.CharField(blank=True, default='', max_length=10, verbose_name='商户号 MCH ID'),
        ),
        migrations.AlterField(
            model_name='wechatapp',
            name='trade_type',
            field=models.CharField(choices=[('JSAPI', '公众号JSAPI'), ('NATIVE', '扫码支付'), ('APP', 'APP支付'), ('WAP', '网页WAP'), ('MINIAPP', '微信小程序')], max_length=10, verbose_name='支付方式'),
        ),
        migrations.AlterField(
            model_name='wechatapp',
            name='type',
            field=models.CharField(choices=[('APP', '移动应用'), ('NATIVE', '网站应用'), ('BIZ', '公众账号'), ('MINIAPP', '微信小程序')], help_text='参照 http://open.weixin.qq.com 管理中心的应用类型', max_length=10, verbose_name='开放平台类型'),
        ),
        migrations.AlterField(
            model_name='wechatapp',
            name='verify_key',
            field=models.CharField(blank=True, default='', max_length=16, verbose_name='公众平台认证文件编码'),
        ),
        migrations.AddField(
            model_name='wechatapp',
            name='redpack_key',
            field=models.CharField(blank=True, help_text='调用 send_redpack 的时候需要校验客户端提交的 signsign=md5(openid+out_trade_no+amount+nonce_str+redpack_key)', max_length=10, verbose_name='红包秘钥'),
        ),
        migrations.CreateModel(
            name='WechatRedpack',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('out_trade_no', models.CharField(blank=True, max_length=30, null=True, verbose_name='内部订单号')),
                ('result_code', models.CharField(max_length=20, verbose_name='发放结果')),
                ('amount', models.IntegerField(verbose_name='发放金额')),
                ('result', models.TextField(blank=True, verbose_name='发放红包的返回数据')),
                ('app', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='redpacks', to='core.WechatApp', verbose_name='微信APP')),
                ('wechat_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='redpacks', to='core.WechatUser', verbose_name='微信用户')),
            ],
            options={
                'verbose_name': '微信红包记录',
                'verbose_name_plural': '微信红包记录',
                'db_table': 'wxauth_wechat_redpack',
            },
        ),
    ]
