from django.db import models


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

    def get_oauth_redirect_url(self, request=None):
        """ 获取 oauth 回调的完整回调地址
        :return:
        """
        from urllib.parse import urljoin
        from ..views.oauth import auth_callback
        from django.shortcuts import reverse

        return self.oauth_redirect_url or urljoin(
            request and request.get_raw_uri() or '',
            reverse(auth_callback, kwargs=dict(appid=self.app_id))
        )
