from django.contrib import admin
from .models import *


@admin.register(WechatDomain)
class RequestTargetAdmin(admin.ModelAdmin):

    list_display = [
        'id', 'title', 'domain', 'app_id',
    ]


@admin.register(RequestTarget)
class RequestTargetAdmin(admin.ModelAdmin):

    list_display = [
        'id', 'url', 'key',
    ]


@admin.register(WechatUser)
class WechatUserAdmin(admin.ModelAdmin):

    list_display = [
        'openid', 'nickname', 'sex', 'province', 'city',
        'avatar_html_tag',
    ]




