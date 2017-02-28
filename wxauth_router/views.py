import json
import os.path
import time
from urllib.request import urlopen
import urllib.error

from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.http \
    import HttpResponse, JsonResponse, HttpResponseNotFound, HttpResponseBadRequest
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from config.models import Option

from .models import *
from . import utils as u


def index(request):
    """
    首页，接受微信 snsapi 的跳转
    :param request:
    :return:
    """

    # 第一步：获取 code 和 state 之后传入本页面

    code = request.GET.get('code', '')
    state = request.GET.get('state', '')

    # print(code)

    app = WechatApp.objects.filter(
        domain=request.get_host(),
    ).first()

    if not app:
        return HttpResponse(status=404)

    if not code:
        ua = request.META.get('HTTP_USER_AGENT')
        # print(('MicroMessenger' in ua), ua)
        # print(domain.domain, domain.title)
        if 'MicroMessenger' in ua and app:
            return redirect(
                'https://open.weixin.qq.com/connect/oauth2/authorize'
                '?appid=%s&redirect_uri=%s'
                '&response_type=code'
                '&scope=snsapi_userinfo'
                '&state=#wechat_redirect' % (
                    app.app_id,
                    'http%3a%2f%2f' + app.domain,
                )
            )
        return redirect('/admin')

    wxuser = app.get_sns_user(code)
    if not wxuser:
        return HttpResponseBadRequest('获取用户信息失败，详细错误信息请查看错误日志')

    # 第四步：根据 state 值进行跳转
    # state 的格式：前八位对应 RequestTarget 的 key 后面为传输参数
    target = RequestTarget.objects.filter(key=state[:8]).first()

    if target:
        redirect_uri = target.url
    else:
        # 如果没有指定，采用跳转前写入 session 的 redirect_uri
        redirect_uri = request.session.get('redirect_uri')

    # 截取后段传递的参数
    params = state[8:] or request.session.get('wxauth_params') or ''

    if redirect_uri:
        return redirect(
            redirect_uri + '%sticket=%s&state=%s' % (
                '&' if '?' in redirect_uri else '?',
                ResultTicket.make(wxuser).key,
                params
            )
        )

    return HttpResponseBadRequest('验证回跳地址没有指定')


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

    return HttpResponse(json.dumps(wxuser.serialize()))


def preview(request):
    """
    redirect 到这个回调，可以预览结果
    """
    return redirect(reverse(
        ticket, kwargs={'key': request.GET.get('ticket')}
    ))


def verify_key(request, key):
    """
    将文件 MP_verify_xxxxxxxxx 上传至填写域名或路径指向的 web 服务器
    :param request:
    :return:
    """
    app = WechatApp.objects.filter(domain=request.get_host()).first()
    assert key and key == app.verify_key, '验证码不正确'
    return HttpResponse(key)


def make_order(request, appid):
    app = WechatApp.objects.filter(app_id=appid).first()
    if app:
        return JsonResponse(app.make_order(
            body=request.GET.get('body'),
            total_fee=request.GET.get('total_fee'),
            out_trade_no=request.GET.get('out_trade_no'),
            user_id=request.GET.get('user_id'),
            product_id=request.GET.get('product_id'),
        ), safe=False)
    app = AlipayApp.objects.filter(app_id=appid).first()
    if app:
        args = app.make_order_wap(
            subject=request.GET.get('subject'),
            out_trade_no=request.GET.get('out_trade_no'),
            total_amount=request.GET.get('total_amount'),
            body=request.GET.get('body', ''),
        )
        return HttpResponse(u.dict_to_url(args))
    app = AlipayMapiApp.objects.filter(app_id=appid).first()
    if app:
        return HttpResponse(app.make_order_www_url(
            subject=request.GET.get('subject'),
            out_trade_no=request.GET.get('out_trade_no'),
            total_amount=request.GET.get('total_amount'),
            body=request.GET.get('body', ''),
        ))
    return HttpResponse('APPID未注册', status=400)


def make_order_form(request, appid):
    """
    生成支付的 html 元素，将此 HTML 元素附加到页面中，自动调起支付
    :param request:
    :param appid:
    :return:
    """
    # import re
    # from urllib.parse import urljoin, quote_plus
    # app = AlipayMapiApp.objects.filter(app_id=appid).first()
    # if app:
    #     args = app.make_order_www(
    #         subject=request.GET.get('subject', ''),
    #         body=request.GET.get('body', ''),
    #         out_trade_no=request.GET.get('out_trade_no'),
    #         total_amount=float(request.GET.get('total_amount')),
    #     )
    #     return HttpResponse(u.make_form(args, 'https://mapi.alipay.com/gateway.do'))

    # app = AlipayApp.objects.filter(app_id=appid).first()
    # if app:
    #     sign_url = app.make_order_wap(
    #         subject=request.GET.get('subject'),
    #         out_trade_no=request.GET.get('out_trade_no'),
    #         total_amount=request.GET.get('total_amount'),
    #         body=request.GET.get('body', ''),
    #     )
    #     html = ''
    #     for row in sign_url.split('&'):
    #         [(key, val)] = re.findall(r'^([^=+])=(.+)$', row)
    #         html += '<input type="hidden" value=\'{}\' />'

    return HttpResponse('', status=400)


@csrf_exempt
def verify_notify(request, appid):
    """
    验签 notify
    :param request:
    :param appid:
    :return: 返回 JSON: dict(success: true/false, out_trade_no: <str>, amount: <number>)
    """
    app = AlipayMapiApp.objects.filter(app_id=appid).first()
    if app:
        return JsonResponse(app.verify_notify(request))
    return HttpResponse('不支持的APP类型', status=400)


def verify_return(request, appid):
    """
    验签 return
    :param request:
    :param appid:
    :return: 返回 JSON: dict(success: true/false, out_trade_no: <str>, amount: <number>)
    """
    app = AlipayMapiApp.objects.filter(app_id=appid).first()
    if app:
        return JsonResponse(app.verify_return(request))
    return HttpResponse('不支持的APP类型', status=400)


def query_order(request, appid):
    app = WechatApp.objects.filter(app_id=appid).first()
    if app:
        return JsonResponse(app.query_order(
            out_trade_no=request.GET.get('out_trade_no', ''),
        ), safe=False)
    app = AlipayApp.objects.filter(app_id=appid).first()
    if app:
        return JsonResponse(app.query_order(
            out_trade_no=request.GET.get('out_trade_no', ''),
        ), safe=False)
    return HttpResponse('APPID未注册', status=400)


def auth(request, appid):
    """
    直接带 appid 跳转到本 view 可以引导至微信公众号 OAuth 验证
    :param request:
    :param appid:
    :return:
    """
    # 记录传入的 redirect_uri
    redirect_uri = \
        request.POST.get('redirect_uri') \
        or request.GET.get('redirect_uri') \
        or request.META.get('HTTP_REFERER')
    assert redirect_uri, \
        '没有找到回调地址，请从 POST.redirect_uri，GET.redirect_uri，' \
        'HTTP_REFERER 中选一个传入'
    request.session['redirect_uri'] = redirect_uri

    # 记录传入的 params
    request.session['wxauth_params'] = \
        request.POST.get('params') \
        or request.GET.get('params')

    from urllib.parse import urljoin, quote_plus
    auth_uri = (
        'https://open.weixin.qq.com/connect/oauth2/authorize'
        '?appid={}'
        '&redirect_uri={}'
        '&response_type=code'
        '&scope=snsapi_userinfo'
        '&state=#wechat_redirect'
    ).format(
        appid,
        quote_plus(urljoin(request.get_raw_uri(), reverse(index))),
    )
    return redirect(auth_uri)


def sns_user(request, appid, code):
    """
    根据 OAuth 接口请求回来的 code 获取用的信息
    :param request:
    :param appid:
    :param code:
    :return:
    """
    app = WechatApp.objects.get(app_id=appid)
    wxuser = app.get_sns_user(code)
    return HttpResponse(
        json.dumps(wxuser.serialize())
        if wxuser else '获取用户信息失败，可能是 code 已失效'
    )
