from django.contrib import admin
from .models import *


@admin.register(WechatDomain)
class RequestTargetAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'domain', 'app_id', 'verify_key',
    ]


@admin.register(RequestTarget)
class RequestTargetAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'url', 'key',
    ]


@admin.register(WechatUser)
class WechatUserAdmin(admin.ModelAdmin):
    list_display = [
        'openid', 'avatar_html_tag',
        'nickname', 'domain', 'sex', 'province', 'city',
        'timestamp',
    ]


@admin.register(WechatApp)
class WechatAppAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'trade_type', 'app_id',
    ]
