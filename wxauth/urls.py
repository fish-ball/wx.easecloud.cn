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

import core.views


urlpatterns = [
    url(r'^$', core.views.index),
    url(r'^wechat_demo_order/(?P<appid>.+)/$', core.views.wechat_demo_order),
    url(r'^make_order/(?P<appid>.+)/$', core.views.make_order),
    url(r'^make_wechat_withdraw_ticket/(?P<appid>.+)/(?P<code>.+)/$', core.views.make_wechat_withdraw_ticket),
    url(r'^apply_wechat_withdraw/(?P<withdraw_key>.+)/(?P<sign>.+)/$', core.views.apply_wechat_withdraw),
    # url(r'^make_order_form/(?P<appid>.+)/$', core.views.make_order_form),
    url(r'^notify/(?P<appid>.+)/$', core.views.notify),
    url(r'^query_order/(?P<appid>.+)/$', core.views.query_order),
    url(r'^verify_notify/(?P<appid>.+)/$', core.views.verify_notify),
    url(r'^verify_return/(?P<appid>.+)/$', core.views.verify_return),
    url(r'^sns_user/(?P<appid>.+)/(?P<code>.+)/$', core.views.sns_user),
    url(r'^auth/(?P<appid>.+)/$', core.views.auth),
    url(r'^ticket/(?P<key>.+)/$', core.views.ticket),
    url(r'^wx_jssdk/(?P<appid>.+)/$', core.views.wx_jssdk),
    url(r'^wx_jssdk_script/(?P<appid>.+)/$', core.views.wx_jssdk_script),
    url(r'^user/(?P<appid>.+)/(?P<unionid>.+)/$', core.views.user),
    url(r'^preview/$', core.views.preview),
    url(r'^MP_verify_(?P<key>.+)\.txt$', core.views.verify_key),
    url(r'^admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += \
        static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += \
        static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
