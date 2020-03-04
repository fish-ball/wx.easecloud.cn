import hashlib
import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import WechatApp


@csrf_exempt
def send_redpack(request, appid):
    """ 向指定的用户发放红包
    POST 参数：
    openid: 接收用户的 id
    out_trade_no: 唯一红包订单号
    amount: 红包金额（分）
    nonce_str: 随机字符串（建议长度为10）
    sign: md5(openid+out_trade_no+amount+nonce_str+redpack_key)
    name: 红包商户名称
    act_name: 活动名称
    wishing: 红包祝福语
    remark: 红包备注
    :param request:
    :param appid:
    :return:
    """
    app = WechatApp.objects.get(app_id=appid)
    # 关键字段
    openid = request.POST.get('openid') or ''
    out_trade_no = request.POST.get('out_trade_no') or ''
    amount = int(request.POST.get('amount') or '0')
    nonce_str = request.POST.get('nonce_str') or ''
    sign = request.POST.get('sign') or ''
    # 非关键字段
    name = request.POST.get('name') or ''
    act_name = request.POST.get('act_name') or ''
    wishing = request.POST.get('wishing') or ''
    remark = request.POST.get('remark') or ''
    # 校验签名
    sign_valid = hashlib.md5(
        '{}{}{}{}{}'.format(openid, out_trade_no, amount, nonce_str, app.redpack_key).encode()
    ).hexdigest()
    if sign.lower() != sign_valid:
        return HttpResponse('红包密钥签名验证失败', status=400)
    from wechatpy import WeChatPayException
    try:
        redpack = app.send_redpack(openid, amount, name, act_name, wishing, remark, out_trade_no)
    except WeChatPayException as e:
        return JsonResponse(e.__dict__, status=400)
    return JsonResponse(json.loads(redpack.result))
