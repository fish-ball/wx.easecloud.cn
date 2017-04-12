"""
微信网页授权接口路由器
https://mp.weixin.qq.com/wiki?t=resource/res_main&id=mp1421140842&token=&lang=zh_CN
"""

from datetime import datetime, timedelta
import json
import os.path
from django.db import models

from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA

import base64
from base64 import b64decode, b64encode

from django.core.exceptions import ValidationError
from django.shortcuts import Http404
from django.conf import settings

from base64 import b64decode, b64encode

from rest_framework.response import Response

from paypal.standard.ipn.signals import valid_ipn_received


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
        from .middleware import get_request
        from .views import index
        from django.shortcuts import reverse
        return self.oauth_redirect_url or \
               urljoin(get_request().get_raw_uri(), reverse(index))


class PayPalStandardApp(PlatformApp):
    """ PayPal Standard 支付，仅通过收款者邮箱即可完成支付
    注意：需要自编一个 APP_ID，然后 APP_SECRET 采用邮箱
    """

    is_sandbox = models.BooleanField(
        verbose_name='是否沙盒测试环境',
        default=False,
    )

    class Meta:
        verbose_name = 'PayPal Standard APP'
        verbose_name_plural = 'PayPal Standard APP'
        db_table = 'wxauth_paypal_standard_app'

    @staticmethod
    def ipn_received_connector(sender, **kwargs):
        from urllib.request import urlopen
        from urllib.parse import urljoin
        ipn_obj = sender
        app = PayPalStandardApp.objects.filter(
            app_secret=ipn_obj.receiver_email,
        ).first()
        notify_url = urljoin(app.notify_url, '?out_trade_no=' + ipn_obj.invoice)
        print(notify_url)
        urlopen(notify_url)

    def query_order(self, out_trade_no):
        from paypal.standard.ipn.models import PayPalIPN
        from django.forms import model_to_dict
        ipn = PayPalIPN.objects.get(invoice=out_trade_no)
        return model_to_dict(ipn)

    def make_order(self, subject, out_trade_no, total_amount,
                   body='', from_currency='CNY', to_currency='USD',
                   locale='zh_CN'):
        from paypal.standard.forms import PayPalPaymentsForm
        from urllib.parse import urljoin
        from .middleware import get_request
        from django.shortcuts import reverse

        settings.PAYPAL_TEST = self.is_sandbox

        request = get_request()
        notify_url = urljoin(request.build_absolute_uri(), reverse('paypal:paypal-ipn'))

        # 字段参照
        # https://developer.paypal.com/webapps/developer/docs/classic/paypal-payments-standard/integration-guide/Appx_websitestandard_htmlvariables/#paypal-checkout-page-variables
        total_amount = max(0.01,
                           CurrencyRate.convert(total_amount, from_currency, to_currency))
        form_data = dict(
            business=self.app_secret,
            amount=total_amount,
            currency_code=to_currency,
            lc=locale,
            rm=2,
            item_name=subject,
            invoice=out_trade_no,
            notify_url=notify_url,
            return_url=urljoin(self.return_url, '?out_trade_no=' + out_trade_no),
            cancel_return=self.cancel_url,
            custom=body,
            charset='utf-8',
        )
        print(form_data)
        form = PayPalPaymentsForm(initial=form_data)
        return form.render()


# 注册 ipn 通知路由
# valid_ipn_received.connect(PayPalStandardApp.ipn_received_connector)


class PayPalApp(PlatformApp):
    VERIFY_URL_PROD = 'https://www.paypal.com/cgi-bin/webscr'
    VERIFY_URL_TEST = 'https://www.sandbox.paypal.com/cgi-bin/webscr'

    is_sandbox = models.BooleanField(
        verbose_name='是否沙盒测试环境',
        default=False,
    )

    class Meta:
        verbose_name = 'PayPal APP'
        verbose_name_plural = 'PayPal APP'
        db_table = 'wxauth_paypal_app'

    def get_sdk(self):
        import paypalrestsdk
        paypalrestsdk.configure(dict(
            mode='sandbox' if self.is_sandbox else 'live',
            client_id=self.app_id,
            client_secret=self.app_secret,
            openid_redirect_uri=self.get_oauth_redirect_url(),
        ))
        return paypalrestsdk

    def get_oauth_login_url(self):
        return self.get_sdk().Tokeninfo.authorize_url(dict(
            scope='openid profile',
        ))

    def get_token_by_code(self, code):
        sdk = self.get_sdk()
        token = sdk.Tokeninfo.create(code)
        access_token = token.access_token
        print(token)
        print(access_token)
        # self.make_order('我的订单', '112-23', 0.01)
        # return dict()
        return token

    @staticmethod
    def verify(request):
        pass

    def make_order(self, subject, out_trade_no, total_amount, body='', from_currency='CNY', to_currency='USD'):
        """
        下单，返回 PAY_ID
        :return:
        """
        sdk = self.get_sdk()
        total_amount = max(0.01, CurrencyRate.convert(total_amount, from_currency, to_currency))
        payment = sdk.Payment(dict(
            intent='sale',
            payer=dict(payment_method='paypal'),
            transactions=[dict(
                item_list=dict(
                    items=[dict(
                        name='普通订单',
                        sku=out_trade_no,
                        price=total_amount,
                        currency=to_currency,
                        quantity=1,
                    )],
                ),
                amount=dict(
                    total=total_amount,
                    currency=to_currency,
                    # details=dict(
                    #     subtotal='0.01',
                    #     tax='0',
                    #     shipping='0',
                    #     handling_fee='0',
                    #     shipping_discount='0',
                    #     insurance='0',
                    # )
                ),
                description=subject,
            )],
            note_to_payer=body,
            redirect_urls=dict(
                return_url=self.return_url,
                cancel_url=self.return_url,
            ),
        ))
        if payment.create():
            # print('failed')
            # print(payment.links[1].href)
            # print('create success')
            # print(payment.to_dict())
            return payment.to_dict()
            # return payment.links[1].href

        # print(payment.error)
        # print('failed')
        # print(payment)
        raise ValidationError(payment.error)


class CmbPayApp(PlatformApp):
    """ 招行一网通支付
    APPID: branchNo-merchantNo，例如 0757-000002
    APPSecret 为商户秘钥
    """

    is_sandbox = models.BooleanField(
        verbose_name='是否沙箱环境',
        default=False,
    )

    class Meta:
        verbose_name = '招行一网通APP'
        verbose_name_plural = '招行一网通APP'
        db_table = 'wxauth_cmbpay_app'

    def branch_no(self):
        return self.app_id.split('-')[0]

    def merchant_no(self):
        return self.app_id.split('-')[-1]

    def make_req_data(self, out_trade_no, total_amount, agr_no, merchant_serial_no):
        """
        [example request]
        http://127.0.0.1:8000/make_order/0757-000002/?out_trade_no=9999000001&merchant_serial_no=20160804143807&total_amount=0.01&agr_no=64656
        [example payload] - output
        jsonRequestData={"reqData":{"payNoticePara":"","expireTimeSpan":"","merchantNo":"000002","signNoticePara":"","userID":"","clientIP":"","merchantSerialNo":"20160804143807","returnUrl":"http://app.hwc.easecloud.cn/api/payment_record/notify/","mobile":"","agrNo":"64656","lon":"","merchantCssUrl":"","merchantBridgeName":"","date":"20170412","riskLevel":"","branchNo":"0757","dateTime":"20170412000403","orderNo":"9999000001","cardType":"","signNoticeUrl":"http://app.hwc.easecloud.cn/api/payment_record/notify/","amount":"0.01","lat":"","payNoticeUrl":"http://app.hwc.easecloud.cn/api/payment_record/notify/"},"version":"1.0","sign":"f5b3c1da0432ae16f6fcc8f1188ef3038cbe1088dfc679c7f1f278ec9036094f","signType":"SHA-256","charset":"UTF-8"}
        [sandbox gateway]
        http://121.15.180.66:801/netpayment/BaseHttp.dll?MB_EUserPay
        :param out_trade_no:
        :param total_amount:
        :param agr_no:
        :param merchant_serial_no:
        :return:
        """
        return dict(
            dateTime=datetime.now().strftime('%Y%m%d%H%M%S'),
            branchNo=self.branch_no(),
            merchantNo=self.merchant_no(),
            date=datetime.now().strftime('%Y%m%d'),
            orderNo='{:010d}'.format(int(out_trade_no)),
            amount=total_amount,
            expireTimeSpan='',
            payNoticeUrl=self.notify_url,  # 支付通知
            payNoticePara='',
            returnUrl=self.return_url,
            clientIP='',
            cardType='',
            agrNo=agr_no,  # 协议号 例如 46587
            merchantSerialNo=merchant_serial_no,  # 协议开通请求流水号 例如 2016062014308888
            userID='',
            mobile='',
            lon='',
            lat='',
            riskLevel='',
            signNoticeUrl=self.notify_url,  # 签约通知
            signNoticePara='',
            merchantCssUrl='',
            merchantBridgeName='',
        )

    def sign_args(self, req_data):
        # print(req_data)
        str_to_sign = \
            '&'.join(['='.join(item) for item in sorted(req_data.items())]) + \
            '&' + self.app_secret
        from hashlib import sha256
        return sha256(str_to_sign.encode('utf-8')).hexdigest()

    def make_order(self, out_trade_no, total_amount, agr_no, merchant_serial_no):
        req_data = self.make_req_data(
            out_trade_no, total_amount, agr_no, merchant_serial_no)

        data = dict(
            version='1.0',
            charset='UTF-8',
            sign=self.sign_args(req_data),
            signType='SHA-256',
            reqData=req_data,
        )

        return 'jsonRequestData=' + json.dumps(data, separators=(',', ':')),


class AlipayMapiApp(PlatformApp):
    """
    支付宝旧版支付接口（MAPI）产品
    查询 PID 即为 APP_ID，MD5 密钥即为 APP_SECRET
    在何处设置及查看：
    https://openhome.alipay.com/platform/keyManage.htm?keyType=partner
    """

    seller_email = models.CharField(
        verbose_name='卖家支付宝用户号',
        max_length=255,
        blank=True,
        help_text='卖家Email或手机号',
    )

    seller_account_name = models.CharField(
        verbose_name='卖家支付宝账号别名',
        max_length=255,
        blank=True,
    )

    class Meta:
        verbose_name = '支付宝旧版APP'
        verbose_name_plural = '支付宝旧版APP'
        db_table = 'wxauth_alipay_mapi_app'

    def get_alipay(self):
        from alipay import Alipay
        return Alipay(self.app_id, self.app_secret, self.seller_email)

    def make_order_www_url(self, subject, out_trade_no, total_amount, body=''):
        alipay = self.get_alipay()
        extra = dict()
        if body:
            extra['body'] = body
        url = alipay.create_direct_pay_by_user_url(
            out_trade_no=out_trade_no,
            subject=subject,
            total_fee=total_amount,
            notify_url=self.notify_url,
            return_url=self.return_url,
            **extra,
        )
        return url

    def verify_return(self, request):
        alipay = self.get_alipay()
        return dict(
            success=alipay.verify_notify(**dict(request.GET.items())) and
                    request.GET.get('trade_status') == 'TRADE_SUCCESS',
            out_trade_no=request.GET.get('out_trade_no'),
            amount=float(request.GET.get('total_fee')),
        )

    def verify_notify(self, request):
        alipay = self.get_alipay()
        return dict(
            success=alipay.verify_notify(**dict(request.POST.items())) and
                    request.POST.get('trade_status') == 'TRADE_SUCCESS',
            out_trade_no=request.POST.get('out_trade_no'),
            amount=float(request.POST.get('total_fee')),
        )

        # def make_order_www(self, subject, out_trade_no, total_amount, body='', charset='utf-8'):
        #     # TODO: 网站支付
        #     # TODO: 当 subject 或 Body 为中文的时候会挂
        #     """
        #     即时到账交易接口
        #     https://doc.open.alipay.com/docs/doc.htm?spm=a219a.7629140.0.0.lO8V87&treeId=62&articleId=104743&docType=1#s5
        #     :param subject:
        #     :param out_trade_no:
        #     :param total_amount:
        #     :param body:
        #     :param timestamp:
        #     :return:
        #     """
        #     args = dict(
        #         # 基本参数
        #         service='create_direct_pay_by_user',
        #         partner=self.app_id,
        #         _input_charset=charset,
        #         notify_url=self.notify_url,
        #         return_url=self.return_url,
        #         # 业务参数
        #         out_trade_no=out_trade_no,
        #         subject=subject,
        #         body=body,
        #         payment_type='1',
        #         total_fee='{:.2f}'.format(total_amount),
        #         seller_id=self.app_id,
        #     )
        #     return self.alipay_sign_args(args)
        #
        # def md5_sign(self, str):
        #     import hashlib
        #     m = hashlib.md5()
        #     m.update(str.encode())
        #     return m.hexdigest()
        #
        # def alipay_sign(self, args, sign_type='MD5'):
        #     if sign_type == 'MD5':
        #         url = '&'.join(['{}={}'.format(k, v) for k, v in sorted(args.items())]) + self.app_secret
        #         print(url)
        #         return self.md5_sign(url)
        #     else:
        #         raise ValidationError('暂时不支持{}签名方式'.format(sign_type))
        #
        # def alipay_sign_args(self, args, sign_type='MD5'):
        #     return dict(sign=self.alipay_sign(args), sign_type=sign_type, **args)
        #
        # def alipay_sign_url(self, args, sign_type='MD5'):
        #     return '&'.join(['{}={}'.format(k, v) for k, v in
        #                      sorted(self.alipay_sign_args(args, sign_type).items())])


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
        from base64 import b64decode, b64encode
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


class WechatApp(PlatformApp):
    mch_id = models.CharField(
        verbose_name='商户号 MCH ID',
        max_length=50,
        blank=True,
        default='',
    )

    api_key = models.CharField(
        verbose_name='API 密钥',
        max_length=50,
        blank=True,
        default='',
    )

    apiclient_cert = models.TextField(
        verbose_name='PEM 支付证书',
        blank=True,
        default='',
    )

    apiclient_key = models.TextField(
        verbose_name='PEM 支付私钥',
        blank=True,
        default='',
    )

    TRADE_TYPE_JSAPI = 'JSAPI'
    TRADE_TYPE_NATIVE = 'NATIVE'
    TRADE_TYPE_APP = 'APP'
    TRADE_TYPE_WAP = 'WAP'
    TRADE_TYPE_CHOICES = (
        (TRADE_TYPE_JSAPI, '公众号JSAPI'),
        (TRADE_TYPE_NATIVE, '扫码支付'),
        (TRADE_TYPE_APP, 'APP支付'),
        (TRADE_TYPE_WAP, '网页WAP'),
    )

    trade_type = models.CharField(
        verbose_name='支付方式',
        choices=TRADE_TYPE_CHOICES,
        max_length=20,
    )

    TYPE_APP = 'APP'
    TYPE_WEB = 'NATIVE'
    TYPE_BIZ = 'BIZ'
    TYPE_BIZPLUGIN = 'BIZPLUGIN'
    TYPE_CHOICES = (
        (TYPE_APP, '移动应用'),
        (TYPE_WEB, '网站应用'),
        (TYPE_BIZ, '公众账号'),
        # (TYPE_BIZPLUGIN, '公众号第三方平台'),
    )

    type = models.CharField(
        verbose_name='开放平台类型',
        choices=TYPE_CHOICES,
        max_length=20,
        help_text='参照 http://open.weixin.qq.com 管理中心的应用类型'
    )

    ##########################
    # 以下为微信公众号特有字段

    domain = models.CharField(
        verbose_name='公众号网页授权域名',
        max_length=100,
        help_text='公众号 > 开发 > 接口权限 > 网页授权获取用户基本信息',
        # unique=True,
        blank=True,
        null=True,
    )

    verify_key = models.CharField(
        verbose_name='公众平台认证文件编码',
        max_length=20,
        blank=True,
        default='',
    )

    biz_account = models.CharField(
        verbose_name='公众平台微信号',
        max_length=20,
        blank=True,
        default='',
    )

    biz_origin = models.CharField(
        verbose_name='公众平台原始ID',
        max_length=20,
        blank=True,
        default='',
    )

    biz_token = models.CharField(
        verbose_name='公众平台接口令牌',
        max_length=20,
        blank=True,
        default='',
    )

    biz_aes_key = models.CharField(
        verbose_name='公众平台AES密钥',
        max_length=100,
        blank=True,
        default='',
    )

    # access_token = models.CharField(
    #     verbose_name='Access Token',
    #     max_length=255,
    #     default='',
    #     empty=True,
    # )
    #
    # access_token_expire = models.IntegerField(
    #     verbose_name='Access Token Expire',
    #     default=0,
    # )
    #
    # refresh_token = models.IntegerField(
    #     verbose_name='Refresh Token',
    #     default=0,
    # )

    class Meta:
        verbose_name = '微信APP'
        verbose_name_plural = '微信APP'
        db_table = 'wxauth_wechat_app'

    def __str__(self):
        return '[{}] {} {}'.format(
            dict(self.TYPE_CHOICES).get(self.type),
            self.title,
            self.domain,
        )

    def mch_cert(self):
        from django.conf import settings
        path = os.path.join(settings.MEDIA_ROOT, 'wechat/{}/pay/apiclient_cert.pem'.format(self.app_id))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def mch_key(self):
        from django.conf import settings
        path = os.path.join(settings.MEDIA_ROOT, 'wechat/{}/pay/apiclient_key.pem'.format(self.app_id))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def save(self, *args, **kwargs):
        # 将商户证书写入文件
        file_mch_cert = open(self.mch_cert(), 'w')
        file_mch_cert.write(self.apiclient_cert)
        file_mch_cert.close()
        # 将商户私钥写入文件
        file_mch_key = open(self.mch_key(), 'w')
        file_mch_key.write(self.apiclient_key)
        file_mch_key.close()
        super().save(*args, **kwargs)

    def wechat_pay(self):
        from wechatpy import pay
        return pay.WeChatPay(
            appid=self.app_id,
            api_key=self.api_key,
            mch_id=self.mch_id,
            mch_cert=self.mch_cert(),
            mch_key=self.mch_key(),
        )

    def get_oauth_login_url(self):
        auth_uri = (
            'https://open.weixin.qq.com/connect/oauth2/authorize'
            '?appid={}'
            '&redirect_uri={}'
            '&response_type=code'
            '&scope=snsapi_userinfo'
            '&state=#wechat_redirect'
        ).format(
            self.app_id,
            self.get_oauth_redirect_url(),
        )
        return auth_uri

    def make_order(self, body, total_fee,
                   out_trade_no=None, user_id=None, product_id=None):
        """ 统一下单接口
        :param body: 订单描述
        :param total_fee: 金额，单位分
        :param out_trade_no: 外部订单号，默认系统生成
        :param user_id: 用户ID，JSAPI 必传（即付款用户的 open_id）
        :param product_id: 商品ID，NATIVE 必传（自行定义）
        :return:
        """
        from wechatpy import pay
        assert self.trade_type != self.TRADE_TYPE_JSAPI or user_id, \
            'JSAPI 调起下单必须提供 user_id'
        assert self.trade_type != self.TRADE_TYPE_NATIVE or product_id, \
            'NATIVE 调起下单必须提供 product_id'
        wechat_order = pay.api.WeChatOrder(self.wechat_pay())
        if self.trade_type == self.TRADE_TYPE_APP:
            # APP 支付
            order_data = wechat_order.create(
                trade_type=self.trade_type,
                body=body,
                total_fee=total_fee,
                notify_url=self.notify_url,
                out_trade_no=out_trade_no,
            )
            result = wechat_order.get_appapi_params(order_data['prepay_id'])
        elif self.trade_type == self.TRADE_TYPE_NATIVE:
            # 扫码支付
            order_data = wechat_order.create(
                trade_type=self.trade_type,
                body=body,
                total_fee=total_fee,
                notify_url=self.notify_url,
                product_id=product_id,
                out_trade_no=out_trade_no,
            )
            result = wechat_order.get_appapi_params(order_data['prepay_id'])
            # 扫码支付的跳转链接
            result['code_url'] = order_data.get('code_url')
        elif self.trade_type == self.TRADE_TYPE_JSAPI:
            # 公众号 JSAPI 支付
            # 扫码支付
            order_data = wechat_order.create(
                trade_type=self.trade_type,
                body=body,
                user_id=user_id,
                notify_url=self.notify_url,
                total_fee=total_fee,
                out_trade_no=out_trade_no,
            )
            result = self.wechat_pay().jsapi.get_jsapi_params(prepay_id=order_data['prepay_id'])
        else:
            raise ValidationError('不支持的 trade_type: ' + self.trade_type)
        return result

    def query_order(self, out_trade_no, trade_no=''):
        """
        查询订单，
        :param out_trade_no:
        :param trade_no:
        :return:
        """
        from wechatpy import pay
        wechat_order = pay.api.WeChatOrder(self.wechat_pay())
        try:
            result = wechat_order.query(out_trade_no=out_trade_no)
            return dict(result)
        except:
            return None

    def get_jsapi_params(self, prepay_id):
        """ 返回 jsapi 的付款对象 """
        import time
        from wechatpy.pay import api
        from wechatpy.utils import random_string, to_text
        jsapi = api.WeChatJSAPI(self.wechat_pay())
        return jsapi.get_jsapi_params(
            prepay_id=prepay_id,
            nonce_str=random_string(32),
            timestamp=to_text(int(time.time())),
        )

        # def get_native_code_url(self, product_id):
        #     """ 返回 NATIVE 支付调起的链接（可以做成二维码）
        #     对应微信支付系统的模式二：
        #     https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=6_5
        #     :param product_id: 产品编号
        #     """
        #     import time
        #     from wechatpy.utils import random_string, to_text
        #     nonce_str = random_string(32)
        #     timestamp = to_text(int(time.time()))
        #
        #     sign_data = {
        #         'appid': self.app_id,
        #         'mch_id': self.mch_id,
        #         'time_stamp': timestamp,
        #         'nonce_str': nonce_str,
        #         'product_id': product_id
        #     }
        #     from hashlib import md5
        #     signtemp = '&'.join(
        #         ['{}={}'.format(*item) for item in sorted(sign_data.items())] +
        #         ['&key=' + self.api_key]
        #     )
        #     sign = md5(signtemp.encode()).hexdigest().upper()
        #
        #     return 'weixin://wxpay/bizpayurl?' \
        #            'sign=' + sign + \
        #            '&appid=' + self.app_id + \
        #            '&mch_id=' + self.mch_id + \
        #            '&product_id=' + product_id + \
        #            '&time_stamp=' + timestamp + \
        #            '&nonce_str=' + nonce_str

    def get_sns_user(self, code):

        # 换取网页授权 access_token 及 open_id
        url = 'https://api.weixin.qq.com/sns/oauth2/access_token' \
              '?appid=%s&secret=%s&code=%s' \
              '&grant_type=authorization_code' \
              % (self.app_id, self.app_secret, code)

        try:

            from urllib.request import urlopen
            resp = urlopen(url)
            data = json.loads(resp.read().decode())
            assert data.get('access_token'), '获取 access token 失败'
            access_token = data.get('access_token')
            # expires_in = data.get('expires_in')
            # refresh_token = data.get('refresh_token')
            openid = data.get('openid')
            scope = data.get('scope')

            wxuser, created = WechatUser.objects.get_or_create(
                openid=openid, defaults=dict(app=self)
            )

            # 第三步：拉取用户信息
            if 'snsapi_userinfo' in scope:
                url = 'https://api.weixin.qq.com/sns/userinfo' \
                      '?access_token=%s&openid=%s&lang=zh_CN' \
                      % (access_token, openid)

                resp = urlopen(url)
                data = json.loads(resp.read().decode())

                assert data.get('openid'), data.get('errmsg', '获取 access token 失败')

                wxuser.update_info(data)

            return wxuser

        except Exception as ex:

            # 跳过错误并且返回 None (输出到错误流)
            import traceback
            from sys import stderr
            print(traceback.format_exc(), file=stderr)
            return None

    def get_wechat_client(self):
        from wechatpy import WeChatClient
        return WeChatClient(self.app_id, self.app_secret)

    def get_order_info(self, out_trade_no):
        # TODO: 查询微信服务器主动获取订单信息
        pass

    def get_wx_signature(self,
                         method='sha1',
                         timestamp='',
                         nonceStr='',
                         ticket='',
                         request_url=''):
        """
        根据时间戳和随机字符串生成签名
        :param method:
        :return:
        """

        return 'gg'

    def generate_nonce_str(self, length=16):
        """
        默认获取一个长度为16的随机字符串
        :param length:
        :return:
        """
        import random
        chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        nonce_str = ''
        for i in range(0, length - 1):
            nonce_str += chars[random.randint(0, chars.__len__())]
        return nonce_str

    def get_jssdk_config(self, request, debug=None):
        import time
        from wechatpy.utils import random_string, to_text
        from wechatpy.client.api import WeChatJSAPI
        jsapi = WeChatJSAPI(self.get_wechat_client())
        ticket = jsapi.get_jsapi_ticket()
        nonce_str = random_string(32)
        timestamp = to_text(int(time.time()))
        url = request.META.get('HTTP_REFERER')
        signature = jsapi.get_jsapi_signature(nonce_str, ticket, timestamp, url)
        debug = bool(request.GET.get('debug')) if debug is None else debug

        return dict(
            debug=debug,
            appId=self.app_id,
            timestamp=timestamp,
            nonceStr=nonce_str,
            signature=signature,
            jsApiList=[
                'checkJsApi',
                'onMenuShareTimeline',
                'onMenuShareAppMessage',
                'onMenuShareQQ',
                'onMenuShareWeibo',
                'hideMenuItems',
                'showMenuItems',
                'hideAllNonBaseMenuItem',
                'showAllNonBaseMenuItem',
                'translateVoice',
                'startRecord',
                'stopRecord',
                'onRecordEnd',
                'playVoice',
                'pauseVoice',
                'stopVoice',
                'uploadVoice',
                'downloadVoice',
                'chooseImage',
                'previewImage',
                'uploadImage',
                'downloadImage',
                'getNetworkType',
                'openLocation',
                'getLocation',
                'hideOptionMenu',
                'showOptionMenu',
                'closeWindow',
                'scanQRCode',
                'chooseWXPay',
                'openProductSpecificView',
                'addCard',
                'chooseCard',
                'openCard'
            ],
        )


        # def get_wx_config(self):
        #     url = 'https://api.weixin.qq.com/cgi-bin/token' \
        #             '?grant_type=client_credential&' \
        #             'appid={}&secret={}'.format(self.app_id, self.app_secret)
        #     try:
        #         from urllib.request import urlopen
        #         import time
        #         resp = urlopen(url)
        #         data = json.loads(resp.read().decode())
        #         assert data.get('access_token'), '获取 access token 失败'
        #         access_token = data.get('access_token')
        #         url = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket?' \
        #             'access_token={}&type=jsapi'.format(access_token)
        #         resp = urlopen(url)
        #         data = json.loads(resp.read().decode())
        #         assert data.get('ticket'), '获取 ticket 失败'
        #         ticket = data.get('ticket')
        #         request_url = 'gg'
        #         timestamp = time.time().__round__()
        #         nonceStr = self.generate_nonce_str()
        #         signature = self.get_wx_signature(timestamp, nonceStr, ticket, request_url)
        #         wx_config = dict(
        #             appId=self.app_id,
        #             timestamp=timestamp,
        #             nonceStr=nonceStr,
        #             signature=signature,
        #             jsApiList=[
        #                 'checkJsApi',
        #                 'onMenuShareTimeline',
        #                 'onMenuShareAppMessage',
        #                 'onMenuShareQQ',
        #                 'onMenuShareWeibo',
        #                 'hideMenuItems',
        #                 'showMenuItems',
        #                 'hideAllNonBaseMenuItem',
        #                 'showAllNonBaseMenuItem',
        #                 'translateVoice',
        #                 'startRecord',
        #                 'stopRecord',
        #                 'onRecordEnd',
        #                 'playVoice',
        #                 'pauseVoice',
        #                 'stopVoice',
        #                 'uploadVoice',
        #                 'downloadVoice',
        #                 'chooseImage',
        #                 'previewImage',
        #                 'uploadImage',
        #                 'downloadImage',
        #                 'getNetworkType',
        #                 'openLocation',
        #                 'getLocation',
        #                 'hideOptionMenu',
        #                 'showOptionMenu',
        #                 'closeWindow',
        #                 'scanQRCode',
        #                 'chooseWXPay',
        #                 'openProductSpecificView',
        #                 'addCard',
        #                 'chooseCard',
        #                 'openCard'
        #             ]
        #         )
        #         return wx_config
        #
        #     except Exception as ex:
        #
        #         # 跳过错误并且返回 None (输出到错误流)
        #         import traceback
        #         from sys import stderr
        #         print(traceback.format_exc(), file=stderr)
        #         return None


# class WechatDomain(models.Model):
#     """ 微信公众号域 """
#
#     app_id = models.CharField(
#         verbose_name='APP_ID',
#         max_length=50,
#         unique=True,
#     )
#
#     app_secret = models.CharField(
#         verbose_name='APP_SECRET',
#         max_length=50,
#     )
#
#     title = models.CharField(
#         verbose_name='标题',
#         max_length=150,
#         help_text='可以填写公众号的显示名称',
#     )
#
#     domain = models.CharField(
#         verbose_name='域名',
#         max_length=100,
#         help_text='公众号 > 开发 > 接口权限 > 网页授权获取用户基本信息',
#         # unique=True,
#     )
#
#     # access_token = models.CharField(
#     #     verbose_name='Access Token',
#     #     max_length=255,
#     #     default='',
#     #     empty=True,
#     # )
#     #
#     # access_token_expire = models.IntegerField(
#     #     verbose_name='Access Token Expire',
#     #     default=0,
#     # )
#     #
#     # refresh_token = models.IntegerField(
#     #     verbose_name='Refresh Token',
#     #     default=0,
#     # )
#
#     verify_key = models.CharField(
#         verbose_name='认证文件编码',
#         max_length=20,
#         blank=True,
#         default='',
#     )
#
#     class Meta:
#         verbose_name = '公众号域'
#         verbose_name_plural = '公众号域'
#         db_table = 'wxauth_wechat_domain'
#
#     def __str__(self):
#         return self.title + '(' + self.domain + ')'
#
#     def get_wechat_client(self):
#         from wechatpy import WeChatClient
#         return WeChatClient(self.app_id, self.app_secret)


class RequestTarget(models.Model):
    """ 请求目标
    每一个接受转发的回调都需要在这里注册一个 target
    """

    url = models.URLField(
        verbose_name='目标URL',
        # unique=True,
        # max_length=180,
    )

    key = models.CharField(
        verbose_name='目标',
        max_length=8,
        unique=True,
    )

    class Meta:
        verbose_name = '请求目标'
        verbose_name_plural = '请求目标'
        db_table = 'wxauth_request_target'

    def save(self, *args, **kwargs):
        """ 每次保存的时候都自动保存 HASH KEY """
        import hashlib
        md5 = hashlib.md5()
        md5.update(self.url.encode())
        self.key = md5.hexdigest()[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return '[%s] <%s>' % (self.key, self.url)


class WechatUser(models.Model):
    """ 微信用户
    所有验证用户的信息都会缓存在这个位置
    """

    app = models.ForeignKey(
        verbose_name='微信APP',
        to='WechatApp',
        related_name='users',
        null=True,
    )

    # domain = models.ForeignKey(
    #     verbose_name='公众号域',
    #     to='WechatDomain',
    #     related_name='users',
    #     null=True,
    # )

    openid = models.CharField(
        verbose_name='用户OpenID',
        max_length=64,
        primary_key=True,
    )

    nickname = models.CharField(
        verbose_name='用户昵称',
        max_length=128,
        null=True,
    )

    sex = models.IntegerField(
        verbose_name='性别',
        null=True,
        choices=(
            (0, '未知'),
            (1, '男'),
            (2, '女'),
        )
    )

    province = models.CharField(
        verbose_name='省份',
        max_length=120,
        null=True,
    )

    city = models.CharField(
        verbose_name='城市',
        max_length=120,
        null=True,
    )

    country = models.CharField(
        verbose_name='国家',
        max_length=120,
        null=True,
    )

    headimgurl = models.URLField(
        verbose_name='用户头像',
        null=True,
    )

    avatar = models.ImageField(
        verbose_name='头像文件',
        null=True,
        upload_to='avatar'
    )

    privilege = models.TextField(
        verbose_name='用户特权信息',
        null=True,
    )

    unionid = models.CharField(
        verbose_name='用户unionid',
        max_length=64,
        null=True,
    )

    date_created = models.DateTimeField(
        verbose_name='创建日期',
        auto_now_add=True,
    )

    date_updated = models.DateTimeField(
        verbose_name='更新日期',
        auto_now=True,
    )

    class Meta:
        verbose_name = '微信用户'
        verbose_name_plural = '微信用户'
        db_table = 'wxauth_wechat_user'
        ordering = ['-date_updated', '-pk']

    def __str__(self):
        return self.nickname

    def serialize(self):
        from django.forms.models import model_to_dict
        from urllib.parse import urljoin
        from .middleware import get_request
        request = get_request()
        result = model_to_dict(self)
        # 将头像的 url 串接上当前的 domain
        avatar_url = urljoin(request and request.get_raw_uri() or 'http://wx.easecloud.cn', self.avatar_url())
        result['avatar'] = avatar_url
        return result

    def avatar_url(self):
        import os.path
        from django.conf import settings
        return os.path.join(settings.MEDIA_URL, self.avatar.url) \
            if self.avatar else self.headimgurl

    def avatar_html_tag(self):
        return (
            r'<img src="%s" style="max-width: 48px; max-height: 48px;" />'
            % self.avatar_url()
        ) if self.avatar_url() else ''

    avatar_html_tag.short_description = '头像'
    avatar_html_tag.allow_tags = True

    def timestamp(self):
        return self.date_updated.strftime('%Y-%m-%d %H:%M:%S')

    def update_avatar(self, headimgurl):

        from urllib.request import urlopen
        from urllib.error import HTTPError
        from django.core.files import File
        from django.core.files.temp import NamedTemporaryFile
        try:
            resp = urlopen(headimgurl)
            image_data = resp.read()
            temp_file = NamedTemporaryFile(delete=True)
            temp_file.write(image_data)
            try:
                avatar_data = self.avatar and self.avatar.read()
            except FileNotFoundError:
                avatar_data = self.avatar = None
                self.save()
            # 如果头像的二进制更换了才进行更新
            if avatar_data != image_data:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                self.avatar.save(
                    name='%s-%s.png' % (self.openid, timestamp),
                    content=File(temp_file),
                )
                self.save()
        except HTTPError:
            # 出现错误的话删掉存放的头像链接
            self.avatar = None
            self.save()

    def reload_info(self):
        client = self.app.get_wechat_client()
        try:
            data = client.user.get(self.openid)
            if data.get('subscribe'):
                self.update_info(data)
            elif not self.avatar:
                self.update_avatar(self.headimgurl)
        except Exception as ex:
            print(ex)

    def update_info(self, data):

        # 写入所有字段
        for key, val in data.items():
            if hasattr(self, key):
                self.__setattr__(key, val)

        self.save()

        # 保存头像图
        self.update_avatar(data.get('headimgurl'))


class ResultTicket(models.Model):
    """ 结果令牌
    随机 hex
    请求之后返回给客户，客户在超时之前可以获取一次用户的信息
    """
    key = models.CharField(
        verbose_name='令牌值',
        max_length=32,
    )

    user = models.ForeignKey(
        verbose_name='用户',
        to='WechatUser',
        related_name='tickets',
    )

    expires = models.IntegerField(
        verbose_name='超时时间',
    )

    class Meta:
        verbose_name = '结果令牌'

    @classmethod
    def make(cls, user):
        import time, uuid
        return cls.objects.create(
            key=uuid.uuid4().hex,
            user=user,
            expires=int(time.time()) + 60,  # 一分钟内有效
        )

    @classmethod
    def fetch_user(cls, key):
        # 删除所有超时的令牌
        import time
        cls.objects.filter(expires__lt=time.time()).delete()
        ticket = cls.objects.filter(key=key).first()
        return ticket and ticket.user


class AuthLog(models.Model):
    """ 验证日志
    所有验证的请求事件都会保存在这里
    """

    target = models.ForeignKey(
        verbose_name='目标',
        to=RequestTarget,
        related_name='logs',
    )

    state = models.CharField(
        verbose_name='回传state',
        max_length=128,
    )

    timestamp = models.DateTimeField(
        verbose_name='请求时间',
        auto_now_add=True,
    )

    class Meta:
        verbose_name = '验证日志'
        verbose_name_plural = '验证日志'
        db_table = 'wxauth_authlog'
