"""
微信网页授权接口路由器
https://mp.weixin.qq.com/wiki?t=resource/res_main&id=mp1421140842&token=&lang=zh_CN
"""

import json
import os.path
from django.db import models


class WechatApp(models.Model):
    app_id = models.CharField(
        verbose_name='APP_ID',
        max_length=50,
        # unique=True,
    )

    app_secret = models.CharField(
        verbose_name='APP_SECRET',
        max_length=50,
    )

    title = models.CharField(
        verbose_name='标题',
        max_length=150,
        help_text='可以填写公众号的显示名称',
    )

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

    notify_url = models.URLField(
        verbose_name='异步回调URL',
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

    biz_token =models.CharField(
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
            dict(self.TYPE_CHOICES)[self.type],
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
        order_data = wechat_order.create(
            trade_type=self.trade_type,
            body=body,
            total_fee=total_fee,
            notify_url=self.notify_url,
            user_id=user_id,
            product_id=product_id,
            out_trade_no=out_trade_no,
        )
        return wechat_order.get_appapi_params(order_data['prepay_id'])

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
