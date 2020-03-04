import json
import os.path
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.db import models

from .common import PlatformApp


class WechatApp(PlatformApp):
    mch_id = models.CharField(
        verbose_name='商户号 MCH ID',
        max_length=10,
        blank=True,
        default='',
    )

    api_key = models.CharField(
        verbose_name='API 密钥',
        max_length=32,
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
    TRADE_TYPE_MINIAPP = 'MINIAPP'
    TRADE_TYPE_CHOICES = (
        (TRADE_TYPE_JSAPI, '公众号JSAPI'),
        (TRADE_TYPE_NATIVE, '扫码支付'),
        (TRADE_TYPE_APP, 'APP支付'),
        (TRADE_TYPE_WAP, '网页WAP'),
        (TRADE_TYPE_MINIAPP, '微信小程序'),
    )

    trade_type = models.CharField(
        verbose_name='支付方式',
        choices=TRADE_TYPE_CHOICES,
        max_length=10,
    )

    TYPE_APP = 'APP'
    TYPE_WEB = 'NATIVE'
    TYPE_BIZ = 'BIZ'
    TYPE_MINIAPP = 'MINIAPP'
    TYPE_BIZPLUGIN = 'BIZPLUGIN'
    TYPE_CHOICES = (
        (TYPE_APP, '移动应用'),
        (TYPE_WEB, '网站应用'),
        (TYPE_BIZ, '公众账号'),
        (TYPE_MINIAPP, '微信小程序'),
        # (TYPE_BIZPLUGIN, '公众号第三方平台'),
    )

    type = models.CharField(
        verbose_name='开放平台类型',
        choices=TYPE_CHOICES,
        max_length=10,
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
        max_length=16,
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

    withdraw_app = models.ForeignKey(
        verbose_name='提现关联公众号',
        to='self',
        related_name='wxapp',
        blank=True,
        null=True,
        on_delete=models.PROTECT
    )

    template_send_token = models.CharField(
        verbose_name='模板推送令牌',
        max_length=32,
        blank=True,
        help_text='调用 template/<appid>/send 的时候要加上 token=?? 推送'
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

    # 应用内校验字段，如果调用红包发送接口，需要设置这个
    redpack_key = models.CharField(
        verbose_name='红包秘钥',
        max_length=10,
        blank=True,
        help_text='调用 send_redpack 的时候需要校验客户端提交的 sign'
                  'sign=md5(openid+out_trade_no+amount+nonce_str+redpack_key)'
    )

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

    @staticmethod
    def stage_oauth_redirect_info(request):
        """ 暂存传入的回调参数（第三方回调地址 + 参数）
        主要供微信公众号 OAuth 接口使用
        :param request:
        :return:
        """
        # 记录传入的 redirect_uri
        redirect_uri = request.POST.get('redirect_uri') or \
                       request.GET.get('redirect_uri') or \
                       request.META.get('HTTP_REFERER')
        assert redirect_uri, '没有找到回调地址，请从 POST.redirect_uri，' \
                             'GET.redirect_uri，HTTP_REFERER 中选一个传入'
        request.session['oauth_redirect_uri'] = redirect_uri
        # 记录传入的 params
        request.session['oauth_params'] = \
            request.POST.get('params') or request.GET.get('params')
        request.session.modified = True

    @staticmethod
    def restore_oauth_redirect_info(request):
        """ 取回 oauth 回调参数并从 session 注销
        :param request:
        :return: redirect_uri, params
        """
        # 获取 session 保存的跳转前参数并重置 session
        redirect_uri = request.session.get('oauth_redirect_uri') or ''
        params = request.session.get('oauth_params') or ''

        request.session.delete('oauth_redirect_uri')
        request.session.delete('oauth_params')
        request.session.modified = True

        return redirect_uri, params

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
        """ 获取当前微信平台号的 wechatpy.pay.WeChatPay 实例
        http://wechatpy.readthedocs.io/zh_CN/master/pay.html#module-wechatpy.pay
        :return:
        """
        from wechatpy import pay
        return pay.WeChatPay(
            appid=self.app_id,
            api_key=self.api_key,
            mch_id=self.mch_id,
            mch_cert=self.mch_cert(),
            mch_key=self.mch_key(),
        )

    def get_oauth_login_url(self, request=None):
        url = None
        if self.type == self.TYPE_BIZ:
            # 微信公众号
            url = (
                'https://open.weixin.qq.com/connect/oauth2/authorize'
                '?appid={}'
                '&redirect_uri={}'
                '&response_type=code'
                '&scope=snsapi_userinfo'
                '&state=#wechat_redirect'
            ).format(
                self.app_id,
                self.get_oauth_redirect_url(request),
            )
        elif self.type == self.TYPE_WEB:
            # 微信开放平台：网站应用
            url = (
                'https://open.weixin.qq.com/connect/qrconnect'
                '?appid={}'
                '&redirect_uri={}'
                '&response_type=code'
                '&scope=snsapi_login'
                '&state=#wechat_redirect'
            ).format(
                self.app_id,
                self.get_oauth_redirect_url(request),
            )
        else:
            raise ValidationError('微信APP仅支持公众号/网站应用获取OAuth授权地址')
        return url

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

    # def make_transfer(self, openid, amount):
    #     app = self.parent
    #     pay = app.wechat_pay()
    #     amount = int(amount)
    #     result = pay.transfer.transfer(openid, amount, '提现', check_name='NO_CHECK')
    #     return result

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

    def send_redpack(self, openid, amount, name, act_name, wishing, remark, out_trade_no=None):
        result = self.wechat_pay().redpack.send(
            openid, amount, name, act_name, wishing, remark, out_trade_no=out_trade_no)
        redpack, created = self.redpacks.get_or_create(out_trade_no=result.get('mch_billno'))
        redpack.update_info(result)
        return redpack
        # pay.redpack.send(uid, 100,'广西德枞','销售红包奖励','希望你再接再厉哟','感谢您为我们做出的贡献',out_trade_no='abcd1234')
        # OrderedDict([('return_code', 'SUCCESS'),
        # ('return_msg', '该红包已经成功,已经被领取或者发起退款'),
        # ('result_code', 'SUCCESS'),
        # ('err_code', 'SUCCESS'),
        # ('err_code_des', '该红包已经成功,已经被领取或者发起退款'),
        # ('mch_billno', 'abcd1234'),
        # ('mch_id', '1566426571'),
        # ('wxappid', 'wx8466220d6b90ee0f'),
        # ('re_openid', 'oh6qqt-R_XK1VLsom37yjz0sEvno'),
        # ('total_amount', '100')])

    def ensure_user(self, openid):
        wechat_user = self.users.filter(openid=openid).first()
        if not wechat_user:
            client = self.get_wechat_client()
            user = client.user.get(openid)
            self.users.create(**user)
        return wechat_user

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

    def code_to_user(self, code):
        """ 小程序通过 code 获取 Session
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/auth.code2Session.html
        http://docs.wechatpy.org/zh_CN/master/client/wxa.html?highlight=code_to_sess#wechatpy.client.api.WeChatWxa.code_to_session
        """
        try:
            wxsession = self.get_wechat_client().wxa.code_to_session(code)
            session_openid = wxsession['openid']
            session_unionid = wxsession['unionid']

            wxuser, created = self.users.get_or_create(
                openid=session_openid,
                defaults=dict(unionid=session_unionid)
            )
            return wxuser
        except Exception as ex:
            print(ex)
            # 跳过错误并且返回 None (输出到错误流)
            import traceback
            from sys import stderr
            print(traceback.format_exc(), file=stderr)
            return None

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
            assert data.get('access_token'), '获取 access token 失败，{}'.format(json.dumps(data))
            access_token = data.get('access_token')
            # expires_in = data.get('expires_in')
            # refresh_token = data.get('refresh_token')
            openid = data.get('openid')
            scope = data.get('scope')

            wxuser, created = WechatUser.objects.get_or_create(
                openid=openid, defaults=dict(app=self)
            )

            # 第三步：拉取用户信息
            if 'snsapi_userinfo' in scope or scope == 'snsapi_login':
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

    def get_jssdk_config(self, request, debug=None, version='1.0.0'):
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

        api_list = dict(
            checkJsApi=dict(minv='1.0.0', maxv='^'),
            onMenuShareTimeline=dict(minv='1.0.0', maxv='^'),
            onMenuShareAppMessage=dict(minv='1.0.0', maxv='^'),
            onMenuShareQQ=dict(minv='1.0.0', maxv='^'),
            onMenuShareWeibo=dict(minv='1.0.0', maxv='^'),
            hideMenuItems=dict(minv='1.0.0', maxv='^'),
            showMenuItems=dict(minv='1.0.0', maxv='^'),
            hideAllNonBaseMenuItem=dict(minv='1.0.0', maxv='^'),
            showAllNonBaseMenuItem=dict(minv='1.0.0', maxv='^'),
            translateVoice=dict(minv='1.0.0', maxv='^'),
            startRecord=dict(minv='1.0.0', maxv='^'),
            stopRecord=dict(minv='1.0.0', maxv='^'),
            onRecordEnd=dict(minv='1.0.0', maxv='^'),
            playVoice=dict(minv='1.0.0', maxv='^'),
            pauseVoice=dict(minv='1.0.0', maxv='^'),
            stopVoice=dict(minv='1.0.0', maxv='^'),
            uploadVoice=dict(minv='1.0.0', maxv='^'),
            downloadVoice=dict(minv='1.0.0', maxv='^'),
            chooseImage=dict(minv='1.0.0', maxv='^'),
            previewImage=dict(minv='1.0.0', maxv='^'),
            uploadImage=dict(minv='1.0.0', maxv='^'),
            downloadImage=dict(minv='1.0.0', maxv='^'),
            getNetworkType=dict(minv='1.0.0', maxv='^'),
            openLocation=dict(minv='1.0.0', maxv='^'),
            getLocation=dict(minv='1.0.0', maxv='^'),
            hideOptionMenu=dict(minv='1.0.0', maxv='^'),
            showOptionMenu=dict(minv='1.0.0', maxv='^'),
            closeWindow=dict(minv='1.0.0', maxv='^'),
            scanQRCode=dict(minv='1.0.0', maxv='^'),
            chooseWXPay=dict(minv='1.0.0', maxv='^'),
            openProductSpecificView=dict(minv='1.0.0', maxv='^'),
            addCard=dict(minv='1.0.0', maxv='^'),
            chooseCard=dict(minv='1.0.0', maxv='^'),
            openCard=dict(minv='1.0.0', maxv='^'),
            # 1.4.0 added
            updateAppMessageShareData=dict(minv='1.4.0', maxv='^'),
            updateTimelineShareData=dict(minv='1.4.0', maxv='^'),
            onMenuShareQZone=dict(minv='1.4.0', maxv='^'),
            onVoiceRecordEnd=dict(minv='1.4.0', maxv='^'),
            onVoicePlayEnd=dict(minv='1.4.0', maxv='^'),
        )

        return dict(
            debug=debug,
            appId=self.app_id,
            timestamp=timestamp,
            nonceStr=nonce_str,
            signature=signature,
            jsApiList=[k for k, v in api_list.items() if v['minv'] <= version < v['maxv']],
        )

    def make_withdraw_ticket(self, code, amount,
                             expires=timedelta(days=30)):
        """
        产生一条新的待审提现记录
        :param code: 从
        :param amount: 提现的金额，单位是分
        :param expires: 传入一个有效时间区间，默认是30天
        :return:
        """
        import time
        import uuid
        return WechatWithdrawTicket.objects.create(
            key=uuid.uuid4().hex,
            user=self.get_sns_user(code),
            amount=amount,
            expires=int(time.time()) + expires.seconds,
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


class WechatUser(models.Model):
    """ 微信用户
    所有验证用户的信息都会缓存在这个位置
    """

    app = models.ForeignKey(
        verbose_name='微信APP',
        to='WechatApp',
        related_name='users',
        null=True,
        on_delete=models.PROTECT
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

    subscribe = models.BooleanField(
        verbose_name='是否关注',
        default=False,
    )

    nickname = models.CharField(
        verbose_name='用户昵称',
        max_length=128,
        null=True,
        blank=True,
    )

    sex = models.IntegerField(
        verbose_name='性别',
        null=True,
        choices=(
            (0, '未知'),
            (1, '男'),
            (2, '女'),
        ),
        blank=True,
    )

    province = models.CharField(
        verbose_name='省份',
        max_length=120,
        null=True,
        blank=True,
    )

    city = models.CharField(
        verbose_name='城市',
        max_length=120,
        null=True,
        blank=True,
    )

    country = models.CharField(
        verbose_name='国家',
        max_length=120,
        null=True,
        blank=True,
    )

    headimgurl = models.URLField(
        verbose_name='用户头像',
        null=True,
        blank=True,
    )

    avatar = models.ImageField(
        verbose_name='头像文件',
        null=True,
        blank=True,
        upload_to='avatar'
    )

    privilege = models.TextField(
        verbose_name='用户特权信息',
        null=True,
        blank=True,
    )

    unionid = models.CharField(
        verbose_name='用户unionid',
        max_length=64,
        null=True,
        blank=True,
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
        from ..middleware import get_request
        request = get_request()
        result = model_to_dict(self)
        # 将头像的 url 串接上当前的 domain
        avatar_url = urljoin(request and request.get_raw_uri() or 'http://wx.easecloud.cn', self.avatar_url())
        result['avatar'] = avatar_url
        # 计算关联的支付收款用户 openid
        withdraw_user = self.get_withdraw_user()
        result['payment_user_openid'] = withdraw_user and withdraw_user.openid
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
        data = client.user.get(self.openid)
        self.update_info(data)

    def update_info(self, data):
        # 做适当的转化
        data['subscribe'] = bool(int(data.get('subscribe') or 0))

        # 写入所有字段
        for key, val in data.items():
            if hasattr(self, key):
                self.__setattr__(key, val)

        self.save()

        # 保存头像图
        if data.get('headimgurl'):
            self.update_avatar(data.get('headimgurl'))

    def get_withdraw_user(self):
        # 返回当前APP的提现用户对象
        # 如果APP有指定提现使用的微信APP，返回这个提现APP下 union_id 相同的用户
        # 否则，返回 union_id 相同的公众号APP用户
        return self.app.withdraw_app and self.app.withdraw_app.users.filter(
            unionid=self.unionid
        ).first() or WechatUser.objects.filter(
            unionid=self.unionid,
            app__type=WechatApp.TYPE_BIZ
        ).first()


class WechatRedpack(models.Model):
    """ 微信红包记录 """
    app = models.ForeignKey(
        verbose_name='微信APP',
        to='WechatApp',
        related_name='redpacks',
        null=True,
        on_delete=models.PROTECT
    )

    out_trade_no = models.CharField(
        verbose_name='内部订单号',
        max_length=30,
        blank=True,
        null=True,
    )

    result_code = models.CharField(
        verbose_name='发放结果',
        max_length=20
    )

    wechat_user = models.ForeignKey(
        verbose_name='微信用户',
        to='WechatUser',
        related_name='redpacks',
        null=True,
        on_delete=models.PROTECT
    )

    amount = models.IntegerField(
        verbose_name='发放金额',
    )

    result = models.TextField(
        verbose_name='发放红包的返回数据',
        blank=True,
    )

    class Meta:
        verbose_name = '微信红包记录'
        verbose_name_plural = '微信红包记录'
        db_table = 'wxauth_wechat_redpack'

    def update_info(self, data):
        """ 根据发放红包返回的报文更新订单信息 """
        self.result = json.dumps(data)
        self.result_code = data.get('result_code')
        self.wechat_user = self.app.ensure_user(data.get('re_openid'))
        self.amount = int(data.get('total_amount'))
        self.save()


class WechatWithdrawTicket(models.Model):
    """ 提现票据
    有一个有效期，记录了对应的提现用户以及提现金额
    审批提现需要有 APP_SECRET 的参与签名
    """
    key = models.CharField(
        verbose_name='令牌值',
        max_length=32,
    )

    user = models.ForeignKey(
        verbose_name='提现用户',
        to='WechatUser',
        related_name='withdraw_tickets',
        on_delete=models.PROTECT,
    )

    expires = models.IntegerField(
        verbose_name='超时时间',
    )

    amount = models.IntegerField(
        verbose_name='提现金额',
        help_text='单位：分',
    )

    # order_id = models.DateTimeField(
    #     verbose_name='提现单号',
    # )
    #

    STATUS_PENDING = 'PENDING'
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_FAIL = 'FAIL'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = (
        (STATUS_PENDING, '申请中'),
        (STATUS_SUCCESS, '成功'),
        (STATUS_FAIL, '失败'),
        (STATUS_REJECTED, '驳回'),
    )

    status = models.TextField(
        verbose_name='提现状态',
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    #
    # result = models.TextField(
    #     verbose_name='提现结果对象'
    # )
    #
    # date_approve = models.DateTimeField(
    #     verbose_name='审批时间',
    #     blank=True,
    #     null=True,
    # )

    def __str__(self):
        return self.key

    @classmethod
    def make(cls, user, amount):
        import time, uuid
        return cls.objects.create(
            key=uuid.uuid4().hex,
            user=user,
            amount=amount,
            expires=int(time.time()) + 60 * 60 * 24 * 7,  # 7天内有效
        )

    def make_sign(self):
        """ 生成当前提现票据的签名
        规则：MD5('<APPID>&<APP_SECRET>&<OPENID>&<AMOUNT>&<KEY>')
        :return:
        """
        from hashlib import md5
        wxuser = WechatUser.objects.get(
            app=self.user.app.withdraw_app,
            unionid=self.user.unionid
        )
        return md5('{}&{}&{}&{}&{}'.format(
            self.user.app.app_id,
            self.user.app.app_secret,
            wxuser.openid,
            self.amount,
            self.key
        ).encode()).hexdigest().upper()

    def apply(self, sign, approve=True):
        """
        执行一个提现
        :param key:
        :param approve: 执行提现传入 True，拒绝提现返回
        :return: 是否处理成功（仅当远端提现请求处理失败时返回失败）
        """
        assert sign == self.make_sign(), '签名不正确'
        assert self.status == self.STATUS_PENDING, '状态不正确'
        import time
        assert time.time() < self.expires, '提现请求已超时'

        if not approve:
            self.status = self.STATUS_REJECTED
            self.save()
            return True

        # 执行提现并登记结果
        app = self.user.app.withdraw_app
        pay = app.wechat_pay()
        wxuser = WechatUser.objects.get(app=app, unionid=self.user.unionid)
        try:
            pay.transfer.transfer(
                wxuser.openid,
                self.amount,
                '提现 {} 元'.format(self.amount / 100),
                check_name='NO_CHECK',
            )
            self.status = self.STATUS_SUCCESS
            self.save()
            return True
        except Exception as e:
            return False

    class Meta:
        verbose_name = '提现票据'
        db_table = 'wxauth_wechat_withdraw_ticket'


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
        on_delete=models.CASCADE,
    )

    expires = models.IntegerField(
        verbose_name='超时时间',
    )

    class Meta:
        verbose_name = '结果令牌'
        db_table = 'wxauth_result_ticket'

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
