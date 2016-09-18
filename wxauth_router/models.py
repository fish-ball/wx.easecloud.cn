"""
微信网页授权接口路由器
https://mp.weixin.qq.com/wiki?t=resource/res_main&id=mp1421140842&token=&lang=zh_CN
"""

from django.db import models


class WechatDomain(models.Model):
    """ 微信公众号域 """

    title = models.CharField(
        verbose_name='标题',
        max_length=150,
        help_text='可以填写公众号的显示名称',
    )

    domain = models.CharField(
        verbose_name='域名',
        max_length=150,
        help_text='公众号 > 开发 > 接口权限 > 网页授权获取用户基本信息',
        unique=True,
    )

    app_id = models.CharField(
        verbose_name='公众号 APP_ID',
        max_length=50,
        unique=True,
    )

    app_secret = models.CharField(
        verbose_name='公众号 APP_SECRET',
        max_length=50,
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
        verbose_name = '公众号域'
        verbose_name_plural = '公众号域'
        db_table = 'wxauth_wechat_domain'

    def __str__(self):
        return self.title + '(' + self.domain + ')'


class RequestTarget(models.Model):
    """ 请求目标
    每一个接受转发的回调都需要在这里注册一个 target
    """

    url = models.URLField(
        verbose_name='目标URL',
        unique=True,
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

    domain = models.ForeignKey(
        verbose_name='公众号域',
        to='WechatDomain',
        related_name='users',
        null=True,
    )

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

    class Meta:
        verbose_name = '微信用户'
        verbose_name_plural = '微信用户'
        db_table = 'wxauth_wechat_user'

    def __str__(self):
        return self.nickname

    def avatar_html_tag(self):
        return r'<img src="%s" style="max-width: 48px; max-height: 48px;" />' \
               % self.headimgurl \
            if self.headimgurl else ''

    avatar_html_tag.short_description = '头像'
    avatar_html_tag.allow_tags = True


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

