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

    # 获取 session 保存的跳转前参数并重置 session

    oauth_app_id = request.session.get('oauth_app_id') or ''
    request.session.delete('oauth_app_id')

    oauth_redirect_uri = request.session.get('oauth_redirect_uri') or ''
    request.session.delete('oauth_redirect_uri')

    oauth_params = request.session.get('oauth_params')
    request.session.delete('oauth_params')

    # PayPal
    app = PayPalApp.objects.filter(
        app_id=oauth_app_id,
    ).first()

    if app:
        code = request.GET.get('code', '')
        token = app.get_token_by_code(code)
        return redirect(
            oauth_redirect_uri + '%stoken_type=%s&access_token=%s' % (
                '&' if '?' in oauth_redirect_uri else '?',
                token.token_type,
                token.access_token,
            )
        )

    # 微信公众号
    app = WechatApp.objects.filter(
        models.Q(
            models.Q(app_id=oauth_app_id) |
            models.Q(domain=request.get_host())
        ),
        type=WechatApp.TYPE_BIZ,
    ).first()

    if app:

        # 第一步：获取 code 和 state 之后传入本页面
        code = request.GET.get('code', '')
        state = request.GET.get('state', '')

        if not code:
            # @deprecated
            # V1.0 API，直接跳转到首页请求发起 OAuth
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
            else:
                return redirect('/admin')

        wxuser = app.get_sns_user(code)
        if not wxuser:
            return HttpResponseBadRequest(
                ('获取用户信息失败，详细错误信息请查看错误日志' +
                 'code: {}, appid: {}').format(code, oauth_app_id)
            )

        # 第四步：根据 state 值进行跳转
        # state 的格式：前八位对应 RequestTarget 的 key 后面为传输参数
        target = RequestTarget.objects.filter(key=state[:8]).first()

        if target:
            redirect_uri = target.url
        else:
            # 如果没有指定，采用跳转前写入 session 的 redirect_uri
            redirect_uri = oauth_redirect_uri

        # 截取后段传递的参数
        params = state[8:] or oauth_params or ''

        if redirect_uri:
            return redirect(
                redirect_uri + '%sticket=%s&state=%s' % (
                    '&' if '?' in redirect_uri else '?',
                    ResultTicket.make(wxuser).key,
                    params
                )
            )

        return HttpResponseBadRequest('验证回跳地址没有指定')

    return redirect('/admin')


def user(request, appid, unionid):
    """ 提供查询接口，让客户拿到 openid 之后查询用户的信息
    """

    app = WechatApp.objects.get(app_id=appid).withdraw_app

    wxuser = WechatUser.objects.get(
        unionid=unionid, app=app)

    if not wxuser:
        return HttpResponse(status=404)

    return HttpResponse(json.dumps(wxuser.serialize()))


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


def wechat_demo_order(request, appid):
    from hashlib import md5
    from random import random
    app = WechatApp.objects.filter(app_id=appid).first()
    out_trade_no = md5(str(random()).encode()).hexdigest()
    ticket = request.GET.get('ticket')
    if ticket:
        wxuser = ResultTicket.fetch_user(ticket)
        openid = wxuser.openid
        data = app.make_order(
            body='业务购买',
            total_fee=1,
            out_trade_no=out_trade_no,
            user_id=openid,
        )
        return HttpResponse("""
        <script src="/wx_jssdk_script/{}/"/>
        <script>
        wx.ready(function() {
            wx.chooseWXPay({});
        });
        </script>
        {}
        """.format(
            appid,
            json.dumps(data),
            json.dumps(data),
        ))
    else:
        data = app.make_order(
            body='业务购买',
            total_fee=1,
            out_trade_no=out_trade_no,
            product_id=1,
        )
        response = HttpResponse("", status=302)
        response['Location'] = data.get('code_url')
        return response


def make_order(request, appid):
    app = WechatApp.objects.filter(app_id=appid).first()
    if app:
        # 允许临时通过 request 参数改变 trade_type，改而不存
        app.trade_type = request.GET.get('trade_type') or app.trade_type
        return JsonResponse(app.make_order(
            body=request.GET.get('body'),
            total_fee=request.GET.get('total_fee'),
            out_trade_no=request.GET.get('out_trade_no'),
            user_id=request.GET.get('user_id'),
            product_id=request.GET.get('product_id'),
        ), safe=False)
    app = AlipayApp.objects.filter(app_id=appid).first()
    if app:
        if request.GET.get('method', 'wap') == 'wap':
            args = app.make_order_wap(
                subject=request.GET.get('subject'),
                out_trade_no=request.GET.get('out_trade_no'),
                total_amount=request.GET.get('total_amount'),
                body=request.GET.get('body', ''),
            )
            return HttpResponse(u.dict_to_url(args))
        elif request.GET.get('method') == 'app':
            paystr = app.make_order_app(
                subject=request.GET.get('subject'),
                out_trade_no=request.GET.get('out_trade_no'),
                total_amount=request.GET.get('total_amount'),
                body=request.GET.get('body', ''),
            )
            return HttpResponse(paystr)
        raise ValidationError('不支持的支付宝支付类型，请指定 ?method=wap 或 ?method=app')
    app = AlipayMapiApp.objects.filter(app_id=appid).first()
    if app:
        return HttpResponse(app.make_order_www_url(
            subject=request.GET.get('subject'),
            out_trade_no=request.GET.get('out_trade_no'),
            total_amount=request.GET.get('total_amount'),
            body=request.GET.get('body', ''),
        ))
    app = PayPalApp.objects.filter(app_id=appid).first()
    if app:
        return JsonResponse(app.make_order(
            subject=request.GET.get('subject'),
            out_trade_no=request.GET.get('out_trade_no'),
            total_amount=request.GET.get('total_amount'),
            body=request.GET.get('body', ''),
            from_currency=request.GET.get('from_currency', 'CNY'),
            to_currency=request.GET.get('to_currency', 'USD'),
        ))
    app = PayPalStandardApp.objects.filter(app_id=appid).first()
    if app:
        return HttpResponse(app.make_order(
            subject=request.GET.get('subject'),
            out_trade_no=request.GET.get('out_trade_no'),
            total_amount=request.GET.get('total_amount'),
            body=request.GET.get('body', ''),
            from_currency=request.GET.get('from_currency', 'CNY'),
            to_currency=request.GET.get('to_currency', 'USD'),
        ))
    app = CmbPayApp.objects.filter(app_id=appid).first()
    if app:
        return HttpResponse(app.make_order(
            out_trade_no=request.GET.get('out_trade_no'),
            total_amount=request.GET.get('total_amount'),
            agr_no=request.GET.get('agr_no'),
            merchant_serial_no=request.GET.get('merchant_serial_no'),
        ))
    return HttpResponse('APPID未注册', status=400)


def make_wechat_withdraw_ticket(request, appid, code):
    """
    :param appid:
    :param code: 微信 OAuth 获取的 code
    :return:
    """
    # 微信APP
    app = WechatApp.objects.get(
        app_id=appid,
        type=WechatApp.TYPE_APP,
    )

    wxuser = app.get_sns_user(code)
    if not wxuser:
        return HttpResponseBadRequest('获取用户信息失败，详细错误信息请查看错误日志')

    # 前端应用调起申请一个待审提现单，获取单号并且提交到应用后台
    return JsonResponse(dict(key=WechatWithdrawTicket.make(
        wxuser,
        # ... 金额等
        request.GET.get('amount'),
    ).key))


def apply_wechat_withdraw(request, withdraw_key, sign):
    """ 应用后台审批发放一条提现记录，因为需要签名，务必在应用后台调起
    :param request:
    :param withdraw_key:
    :param sign: MD5('<APPID>&<APP_SECRET>&<OPENID>&<AMOUNT>&<KEY>')
    :return:
    """
    assert 'reject' not in request.GET or \
           request.GET.get('reject') != '1', \
        'GET["reject"]参数只能不填或填写 1'
    withdraw_ticket = WechatWithdrawTicket.objects.get(key=withdraw_key)
    success = withdraw_ticket.apply(
        sign=sign,
        approve=request.GET.get('reject') != '1'
    )
    return JsonResponse(dict(
        result='OK',
        msg='处理成功',
    )) if success else JsonResponse(dict(
        result='FAIL',
        msg='处理失败：' + str(),
    ))


@csrf_exempt
def notify(request, appid):
    app = PayPalApp.objects.filter(app_id=appid).first()
    if app:
        print(dict(request.POST.items()))

    return HttpResponse()


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
    app = PayPalStandardApp.objects.filter(app_id=appid).first()
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
    request.session['oauth_redirect_uri'] = redirect_uri
    # 记录传入的 params
    request.session['oauth_params'] = \
        request.POST.get('params') or request.GET.get('params')
    # 记录传入的 oauth_app_id
    request.session['oauth_app_id'] = appid

    # 根据 app 类型进行跳转
    # 微信公众号
    app = WechatApp.objects.filter(app_id=appid).first()
    if app:
        return redirect(app.get_oauth_login_url())
    # PayPal OAuth
    app = PayPalApp.objects.filter(app_id=appid).first()
    if app:
        return redirect(app.get_oauth_login_url())


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


def wx_jssdk(request, appid):
    """
    :param request:
    :param appid:
    :return:
    """
    app = WechatApp.objects.get(app_id=appid)
    wx_config = app.get_jssdk_config(request)
    return JsonResponse(data=wx_config)


def wx_jssdk_script(request, appid):
    app = WechatApp.objects.get(app_id=appid)
    return render(request, 'wxauth_router/wx_jssdk.js', dict(
        wx_config=json.dumps(app.get_jssdk_config(request))
    ), 'application/javascript')
