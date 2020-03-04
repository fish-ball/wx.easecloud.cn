"""wxauth URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings

import core.views.oauth


urlpatterns = [
    # 门户
    url(r'^$', core.views.index),

    # OAuth
    url(r'^auth/(?P<appid>[^/]+)/$', core.views.oauth.auth),
    url(r'^auth/(?P<appid>[^/]+)/callback/$', core.views.oauth.auth_callback),
    url(r'^sns_user/(?P<appid>[^/]+)/(?P<code>[^/]+)/$', core.views.oauth.sns_user),
    url(r'^ticket/(?P<key>[^/]+)/$', core.views.oauth.ticket),
    url(r'^user/(?P<appid>[^/]+)/(?P<user_id>[^/]+)/$', core.views.oauth.user),

    # 模板消息
    url(r'^template/(?P<appid>[^/]+)/list/$', core.views.oauth.template_list),
    url(r'^template/(?P<appid>[^/]+)/send/$', core.views.oauth.template_send),

    # 支付
    url(r'^make_order/(?P<appid>[^/]+)/$', core.views.make_order),
    url(r'^notify/(?P<appid>[^/]+)/$', core.views.notify),
    url(r'^query_order/(?P<appid>[^/]+)/$', core.views.query_order),
    url(r'^verify_notify/(?P<appid>[^/]+)/$', core.views.verify_notify),
    url(r'^verify_return/(?P<appid>[^/]+)/$', core.views.verify_return),

    # 提现
    url(r'^make_wechat_withdraw_ticket/(?P<appid>[^/]+)/(?P<code>[^/]+)/$', core.views.make_wechat_withdraw_ticket),
    url(r'^apply_wechat_withdraw/(?P<withdraw_key>[^/]+)/(?P<sign>[^/]+)/$', core.views.apply_wechat_withdraw),
    url(r'^send_redpack/(?P<appid>[^/]+)/$', core.views.send_redpack),

    # JSSDK
    url(r'^wx_jssdk/(?P<appid>[^/]+)/$', core.views.wx_jssdk),
    url(r'^wx_jssdk_script/(?P<appid>[^/]+)/$', core.views.wx_jssdk_script),

    # 文件认证
    url(r'^MP_verify_(?P<key>[^/]+)\.txt$', core.views.verify_key),

    # 管理后台
    url(r'^admin/', admin.site.urls),

    # 调试用
    url(r'^preview/$', core.views.preview),
    url(r'^wechat_demo_order/(?P<appid>[^/]+)/$', core.views.wechat_demo_order),
]

if settings.DEBUG:
    urlpatterns += \
        static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += \
        static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
