from django.db import models

from .common import PlatformApp


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
