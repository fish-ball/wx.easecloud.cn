from django.http \
    import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .. import utils as u
from ..models import *


def index(request):
    return HttpResponse(r'''<pre>
    _________   _____ ______________    ____  __  ______ 
   / ____/   | / ___// ____/ ____/ /   / __ \/ / / / __ \
  / __/ / /| | \__ \/ __/ / /   / /   / / / / / / / / / /
 / /___/ ___ |___/ / /___/ /___/ /___/ /_/ / /_/ / /_/ / 
/_____/_/  |_/____/_____/\____/_____/\____/\____/_____/  
    </pre>''')


def preview(request):
    """
    redirect 到这个回调，可以预览结果
    """
    from .oauth import ticket
    return redirect(reverse(
        ticket, kwargs={'key': request.GET.get('ticket')}
    ))


def verify_key(request, key):
    """
    将文件 MP_verify_xxxxxxxxx 上传至填写域名或路径指向的 web 服务器
    :param request:
    :return:
    """
    # 直通车算了，没必要搞验证了
    # app = WechatApp.objects.filter(domain=request.get_host()).first()
    # assert key and key == app.verify_key, '验证码不正确'
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
        data = json.dumps(data)
        result = ('<script src="/wx_jssdk_script/' + appid + '/"/>' +
                  '<script>'
                  'wx.ready(function() {'
                  '    wx.chooseWXPay(' + data + ');' +
                  '});'
                  '</script>')
        result = result + '<pre>' + result + '</pre>'
        return HttpResponse(result)
    else:
        app.trade_type = 'NATIVE'
        data = app.make_order(
            body='业务购买',
            total_fee=1,
            out_trade_no=out_trade_no,
            product_id=1,
        )
        return HttpResponse('<a href="{}"><img src="http://qr.liantu.com/api.php?text={}"/></a>'.format(
            data.get('code_url'),
            data.get('code_url')
        ))
        # response = HttpResponse("", status=302)
        # response['Location'] = data.get('code_url')
        # return response


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


def get_wechat_native_oauth_url(request, appid):
    pass


@csrf_exempt
def notify(request, appid):
    """ 接受订单回调
    :param request:
    :param appid:
    :return:
    """
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
    return HttpResponse('APPID未注册', status=400)


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
    version = request.GET.get('version') or '1.0.0'
    return render(request, 'core/jweixin-{}.js'.format(version), dict(
        wx_config=json.dumps(app.get_jssdk_config(request))
    ), 'application/javascript')
