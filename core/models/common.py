import json

from datetime import datetime
from django.db import models


class CurrencyRate(models.Model):
    currency = models.CharField(
        verbose_name='币种',
        max_length=20,
    )

    date = models.DateField(
        verbose_name='汇率时间',
    )

    rate = models.DecimalField(
        verbose_name='汇率（兑1美元）',
        max_digits=18,
        decimal_places=6,
    )

    class Meta:
        verbose_name = '汇率'
        verbose_name_plural = '汇率'
        unique_together = [('currency', 'date')]

    def __str__(self):
        return '[{}]1USD={}{}'.format(self.date.strftime('%Y-%m-%d'), self.rate, self.currency)

    @classmethod
    def get(cls, currency, dt=None):
        dt = dt or datetime.date(datetime.now())
        item = cls.objects.filter(date=dt, currency=currency).first()
        if not item:
            from urllib.request import urlopen
            resp = urlopen('http://apilayer.net/api/live?access_key=fb8eb6b05a91727dd880143c550d828c')
            data = json.loads(resp.read().decode()).get('quotes')
            for k, v in data.items():
                currency = k[3:]
                item = cls.objects.create(date=dt, currency=currency, rate=v)
        return float(item.rate)

    @classmethod
    def convert(cls, amount, from_currency, to_currency, digits=2, dt=None):
        # dt = dt or datetime.date(datetime.now())
        if from_currency != to_currency:
            amount = float(amount) * cls.get(to_currency, dt) / cls.get(from_currency, dt)
        return round(amount, digits)


class PlatformApp(models.Model):
    title = models.CharField(
        verbose_name='标题',
        max_length=150,
        help_text='可以填写公众号的显示名称',
    )

    app_id = models.CharField(
        verbose_name='APP_ID',
        max_length=176,
        unique=True,
    )

    app_secret = models.CharField(
        verbose_name='APP_SECRET',
        max_length=255,
        blank=True,
    )

    notify_url = models.URLField(
        verbose_name='授权回调地址',
        blank=True,
        default='',
    )

    return_url = models.URLField(
        verbose_name='授权跳转地址',
        blank=True,
        default='',
    )

    cancel_url = models.URLField(
        verbose_name='取消操作返回 URL',
        blank=True,
        default='',
    )

    oauth_redirect_url = models.URLField(
        verbose_name='OAuth 认证跳转地址',
        blank=True,
        default='',
        help_text='如果是，请务必将本地址设定为本 API 的 index，例如 http://wx.easecloud.cn'
                  '并且在对应的平台中注册此地址，不填的话默认会使用当前地址',
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    def get_oauth_redirect_url(self):
        from urllib.parse import urljoin
        from ..middleware import get_request
        from ..views import index
        from django.shortcuts import reverse
        return self.oauth_redirect_url or \
               urljoin(get_request().get_raw_uri(), reverse(index))
