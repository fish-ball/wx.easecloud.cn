import json

from datetime import datetime, timedelta
from base64 import b64decode, b64encode

from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from django.db import models

from .common import PlatformApp


class AlipayApp(PlatformApp):
    mch_id = models.CharField(
        verbose_name='商户号 MCH ID',
        max_length=50,
        blank=True,
        default='',
    )

    app_gateway = models.CharField(
        verbose_name='应用网关',
        max_length=150,
        blank=True,
        default='',
        help_text='除服务窗外其他的应用，目前未做强制校验，可以不用填写',
    )

    rsa2_app_key_public = models.TextField(
        verbose_name='RSA2(SHA256)应用公钥',
        blank=True,
        default='',
    )

    rsa2_app_key_private = models.TextField(
        verbose_name='RSA2(SHA256)应用私钥',
        blank=True,
        default='',
    )

    rsa2_alipay_key_public = models.TextField(
        verbose_name='RSA2(SHA256)支付宝公钥',
        blank=True,
        default='',
    )

    rsa_app_key_public = models.TextField(
        verbose_name='RSA(SHA1)应用公钥',
        blank=True,
        default='',
    )

    rsa_app_key_private = models.TextField(
        verbose_name='RSA(SHA1)应用私钥',
        blank=True,
        default='',
    )

    rsa_alipay_key_public = models.TextField(
        verbose_name='RSA(SHA1)支付宝公钥',
        blank=True,
        default='',
    )

    aes_key = models.CharField(
        verbose_name='接口AES密钥',
        max_length=150,
        blank=True,
        default='',
    )

    class Meta:
        verbose_name = '支付宝APP'
        verbose_name_plural = '支付宝APP'
        db_table = 'wxauth_alipay_app'

    def rsa_sign(self, text):
        """ 用当前的 APP 证书 SHA1 签名一个字符串 """
        key = RSA.importKey(b64decode(self.rsa_app_key_private))
        h = SHA.new(text.encode())
        signer = PKCS1_v1_5.new(key)
        return b64encode(signer.sign(h)).decode()

    def rsa_verify(self, text, sign):
        """ 用当前的阿里云公钥 SHA1 验签一个字符串 """
        from base64 import b64decode
        public_key = RSA.importKey(b64decode(self.rsa_alipay_key_public))
        sign = b64decode(sign)
        h = SHA.new(text.encode('GBK'))
        verifier = PKCS1_v1_5.new(public_key)
        return verifier.verify(h, sign)

    def alipay_verify(self, data):
        """ 验签一个阿里云回调数据集 """
        # QueryDict 转 Dict
        data = {k: data[k] for k in data}
        sign = data.pop('sign')
        data.pop('sign_type')
        text = '&'.join(['='.join(item) for item in sorted(data.items())])
        return self.rsa_verify(text, sign or data.get('sign') + '')

    def alipay_sign(self, args):
        return self.rsa_sign('&'.join(['{}={}'.format(k, v) for k, v in sorted(args.items())]))

    def alipay_sign_args(self, args):
        return dict(sign=self.alipay_sign(args), **args)

    def alipay_sign_url(self, args):
        return '&'.join(['{}={}'.format(k, v) for k, v
                         in sorted(self.alipay_sign_args(args).items())])

    def make_order_wap(self, subject, out_trade_no, total_amount, body='', timestamp=None):
        """
        手机网站支付：
        https://doc.open.alipay.com/docs/doc.htm?spm=a219a.7629140.0.0.2Uyr3A&treeId=203&articleId=105287&docType=1
        :param subject:
        :param out_trade_no:
        :param total_amount:
        :param body:
        :param timestamp:
        :return:
        """
        args = dict(
            app_id=self.app_id,
            method='alipay.trade.wap.pay',
            charset='utf-8',
            sign_type='RSA',
            timestamp=(timestamp or datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            version='1.0',
            notify_url=self.notify_url,
            return_url=self.return_url,
            biz_content=json.dumps(dict(
                body=body,
                subject=subject,
                out_trade_no=out_trade_no,
                total_amount='{:.2f}'.format(float(total_amount)),
                product_code='QUICK_WAP_PAY',
            ), separators=(',', ':')),
        )
        return self.alipay_sign_args(args)

    def make_order_app(self, subject, out_trade_no, total_amount, body='', timestamp=None):
        """
        app 支付：
        :param subject:
        :param out_trade_no:
        :param total_amount:
        :param body:
        :param timestamp:
        :return:
        """
        args = dict(
            app_id=self.app_id,
            method='alipay.trade.app.pay',
            charset='utf-8',
            sign_type='RSA',
            timestamp=(timestamp or datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            version='1.0',
            notify_url=self.notify_url,
            biz_content=json.dumps(dict(
                body=body,
                subject=subject,
                out_trade_no=out_trade_no,
                total_amount='{:.2f}'.format(float(total_amount)),
                product_code='QUICK_MSECURITY_PAY',
            ), separators=(',', ':')),
        )
        args = self.alipay_sign_args(args)
        from urllib.parse import quote_plus
        return '&'.join(['{}={}'.format(k, quote_plus(v)) for k, v in sorted(args.items())])

    def query_order(self, out_trade_no, trade_no=''):
        """
        查询订单，
        :param out_trade_no:
        :param trade_no:
        :return:
        """
        import http.client
        http.client.HTTPConnection._http_vsn = 10
        http.client.HTTPConnection._http_vsn_str = 'HTTP/1.1'
        from urllib.request import urlopen
        from urllib.parse import urlencode
        args = dict(
            app_id=self.app_id,
            method='alipay.trade.query',
            charset='utf-8',
            sign_type='RSA',
            timestamp=(datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            version='1.0',
            biz_content=json.dumps(dict(
                out_trade_no=out_trade_no,
                trade_no=trade_no,
            )),
        )
        args['sign'] = self.alipay_sign(args)
        url = 'https://openapi.alipay.com/gateway.do?{}'.format(urlencode(args))
        resp = urlopen(url)
        return json.loads(resp.read().decode())
