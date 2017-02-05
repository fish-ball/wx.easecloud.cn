from django.contrib import admin
from . import models as m


@admin.register(m.WechatApp)
class WechatAppAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'type', 'title', 'trade_type', 'app_id',
    ]


@admin.register(m.WechatDomain)
class RequestTargetAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'domain', 'app_id', 'verify_key',
    ]


@admin.register(m.RequestTarget)
class RequestTargetAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'url', 'key',
    ]


@admin.register(m.WechatUser)
class WechatUserAdmin(admin.ModelAdmin):
    list_display = [
        'openid', 'avatar_html_tag',
        'nickname', 'app', 'domain', 'sex', 'province', 'city',
        'timestamp',
    ]


for model_class in m.__dict__.values():
    if model_class.__class__ == m.models.base.ModelBase \
            and not model_class._meta.abstract:
        try:
            admin.site.register(model_class)
        except admin.sites.AlreadyRegistered as e:
            pass
        except Exception as e:
            print(e)
