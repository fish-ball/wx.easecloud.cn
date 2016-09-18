import json
import time
from urllib.request import urlopen

from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.http \
    import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest
from django.conf import settings

from config.models import Option

from .models import *


def index(request):
    """
    首页，接受微信 snsapi 的跳转
    :param request:
    :return:
    """

    # 第一步：获取 code 和 state 之后传入本页面

    code = request.GET.get('code', '')
    state = request.GET.get('state', '')

    domain = WechatDomain.objects.filter(
        domain=request.get_host(),
    ).first()

    if not domain:
        return HttpResponse(status=404)

    if not code:
        return redirect('/admin')

    # 第二步：换取网页授权 access_token 及 open_id
    url = 'https://api.weixin.qq.com/sns/oauth2/access_token' \
          '?appid=%s&secret=%s&code=%s' \
          '&grant_type=authorization_code' \
          % (domain.app_id, domain.app_secret, code)

    resp = urlopen(url)
    data = json.loads(resp.read().decode())

    if not data.get('access_token'):
        return HttpResponseBadRequest(
            data.get('errmsg', '获取 access token 失败')
        )

    access_token = data.get('access_token')
    # expires_in = data.get('expires_in')
    # refresh_token = data.get('refresh_token')
    openid = data.get('openid')
    scope = data.get('scope')

    wxuser, created = WechatUser.objects.get_or_create(
        openid=openid,
        domain=domain,
    )

    # 第三步：拉取用户信息
    if 'snsapi_userinfo' in scope:

        url = 'https://api.weixin.qq.com/sns/userinfo' \
              '?access_token=%s&openid=%s&lang=zh_CN' \
              % (access_token, openid)

        resp = urlopen(url)
        data = json.loads(resp.read().decode())

        if not data.get('openid'):
            return HttpResponseBadRequest(
                data.get('errmsg', '获取 access token 失败')
            )

        # 写入所有字段
        for key, val in data.items():
            if hasattr(wxuser, key):
                wxuser.__setattr__(key, val)

        wxuser.save()

        # 保存头像图
        from urllib.error import HTTPError
        try:
            resp = urlopen(data.get('headimgurl'))
            wxuser.avatar.save(
                name='avatar-%s.png' % wxuser.openid,
                content=resp.read(),
                save=True
            )
            wxuser.save()
        except HTTPError:
            pass

    # 第四步：根据 state 值进行跳转
    # state 的格式：前八位对应 RequestTarget 的 key 后面为传输参数
    target = RequestTarget.objects.filter(key=state[:8]).first()

    if not target:
        return HttpResponseBadRequest(
            data.get('errmsg', '找不到对应的请求目标，请先注册')
        )

    return redirect(
        target.url + '%sticket=%s&state=%s' % (
            '&' if '?' in target.url else '?',
            ResultTicket.make(wxuser).key,
            state[8:]
        )
    )


# def user(request, openid):
#     """ 提供查询接口，让客户拿到 openid 之后查询用户的信息
#     """
#     wxuser = WechatUser.objects.filter(openid=openid).first()
#
#     if not wxuser:
#         return HttpResponseNotFound()
#
#     from django.forms.models import model_to_dict
#     return HttpResponse(json.dumps(model_to_dict(wxuser)))


def ticket(request, key):
    """ 提供查询接口，让客户拿到 result key 之后查询用户的信息
    """
    wxuser = ResultTicket.fetch_user(key)

    if not wxuser:
        return HttpResponse(status=404)

    from django.forms.models import model_to_dict
    return HttpResponse(json.dumps(model_to_dict(wxuser)))


# def preview(request):
#     """
#     redirect 到这个回调，可以预览结果
#     """
#     return redirect(reverse(user, kwargs={'openid': request.GET.get('openid')}))
