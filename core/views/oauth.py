import json

from django.db import models
from django.http import HttpResponseNotFound, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect

from core.models import WechatApp, ResultTicket


def auth(request, appid):
    """ 微信公众号 OAuth 授权
    直接带 appid 跳转到本 view 可以引导至微信公众号 OAuth 验证
    :param request:
    :param appid:
    :return:
    """
    # 根据 app 类型进行跳转
    # 微信公众号
    app = WechatApp.objects.filter(app_id=appid).first()
    if app:
        app.stage_oauth_redirect_info(request)
        return redirect(app.get_oauth_login_url(request))
    return HttpResponseNotFound()


def auth_callback(request, appid):
    """ 接受并处理 oauth sns_api 的跳转回调
    :param request:
    :param appid: 回调附带的 appid，支持微信公众号以及微信网页 APP
    :return:
    """
    # 微信公众号
    app = WechatApp.objects.filter(app_id=appid).first()
    if app:
        # 第一步：获取 code 和 state 之后传入本页面
        code = request.GET.get('code', '')
        # state = request.GET.get('state', '')

        wxuser = app.get_sns_user(code)
        if not wxuser:
            return HttpResponseBadRequest(
                ('获取用户信息失败，详细错误信息请查看错误日志' +
                 'code: {}, appid: {}').format(code, appid)
            )

        # 获取转发回调参数
        redirect_uri, params = app.restore_oauth_redirect_info(request)

        if not redirect_uri:
            return HttpResponseBadRequest('验证回跳地址没有指定')

        return redirect(
            redirect_uri + '%sticket=%s&state=%s' % (
                '&' if '?' in redirect_uri else '?',
                ResultTicket.make(wxuser).key,
                params
            )
        )
    return HttpResponseNotFound()


def sns_user(request, appid, code):
    """
    根据 OAuth 接口请求回来的 code 获取用户的信息
    :param request:
    :param appid:
    :param code:
    :return:
    """
    app = WechatApp.objects.get(app_id=appid)
    if app:
        wxuser = app.get_sns_user(code)
        return HttpResponse(
            json.dumps(wxuser.serialize())
            if wxuser else '获取用户信息失败，可能是 code 已失效'
        )
    return HttpResponseNotFound()


def ticket(request, key):
    """ 提供查询接口，让客户拿到 result key 之后查询用户的信息
    """
    wxuser = ResultTicket.fetch_user(key)

    if not wxuser:
        return HttpResponse(status=404)

    return HttpResponse(json.dumps(wxuser.serialize()))


def user(request, appid, user_id):
    """ 提供查询接口，让客户拿到 openid/union_id 之后查询用户的信息
    :param request:
    :param appid: APP ID，暂时只支持微信
    :param user_id: 兼容 OpenId 和 UnionID
    :return:
    """
    app = WechatApp.objects.get(app_id=appid)

    wxuser = app.users.filter(
        models.Q(unionid=user_id) |
        models.Q(openid=user_id)
    ).first()

    if not wxuser:
        return HttpResponse(status=404)

    return HttpResponse(json.dumps(wxuser.serialize()))
