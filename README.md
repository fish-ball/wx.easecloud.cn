WeChat SNS API shared by Easecloud Co. Ltd.
===========================================

### API documentation reference:

<https://mp.weixin.qq.com/wiki?t=resource/res_main&id=mp1421140842&token=&lang=zh_CN>

Minimal Example
---------------

Open the link below in the WeChat browser:

##### V2.0:

**Entrance Link:** <http://wx.easecloud.cn/auth/wx579e43a4729b1764/?redirect_uri=/preview>

Ignore the `redirect_uri` param will lead the page returning to `HTTP_REFERER`.

And the returning querystring contains a `ticket=<ticket>` query param, you can fetch the user
authenticated by requesting `http://wx.easecloud.cn/ticket/<ticket>/`.

##### V1.0 (old api):

**Entrance Link:** <https://open.weixin.qq.com/connect/oauth2/authorize?appid=wx579e43a4729b1764&redirect_uri=http%3a%2f%2fwx.easecloud.cn&response_type=code&scope=snsapi_userinfo&state=ba0ab193#wechat_redirect>

Principle
---------

The snsapi of wechat only supports validated service account only.

That means 300RMB per year is required, so for many users who want to get user
information in wechat is a bit hard.

More, when we use the api, only one domain can be bind, if we want to split the
api on several different apps, we must do something to work around it.

For the reasons above, I made a service that share this api, so that many other
app can use the functional, to retrieve the user info who was viewing your page
in wechat browser.

Usage
-----

### V2.0 API:

#### 1. Wechat Official Account OAuth

Since V2.0 wxauth framework does not need to register a specific **REQUEST TARGET**,
(but wx domain with both app_id and api_secret is still required).

Instead, you only need to redirect to the view `http://wx.easecloud.cn/auth/<appid>`.

You can specify the returning url by either:

+ POST params by key `request_uri`
+ or fallbacks to: GET query params by key `request_uri`
+ or fallbacks to: HTTP_REFERER to the origin url

So it triggers the weixin oauth.

Then, if authentication is success, it returns to that returning url, with two
significant query params:

+ ticket: you can fetch the resulting user info(JSON format) by requesting
  http://wx.easecloud.cn/ticket/<ticket>/
+ state: the params that you passed when requesting oauth(optional).

> Note about the state params, you can pass an extra `params` by either POST or GET
params in your origin redirection, e.g.: `http://wx.easecloud.cn/auth/<appid>/?params=goods_id%3D16`

> Then you got the returning state as `goods_id=16` with the ticket.

And you can get the user information by something like(JS example):

```
$.getJSON('http://wx.easecloud.cn/ticket/'+ticket).then(function(user_info) {
    console.log(user_info);
});
```

#### 2. Wechat Pay Uniform ordering

This api calls the wechat uniform ordering(统一下单) API:

Ref: <https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=9_1>

First, you must create a Wechat APP order in the admin panel, which stores the
`appid` and `appsecret`, `mch_id`, payment certificate strings,
and both `notify_url` and `trade_type`(see on the docs above).

Then, by requesting `http://wx.easecloud.cn/make_order/` with the following,
GET query params, you got the uniform ordering uri:

+ body: the display name showed by the order.
+ total_fee: payment amount measured by RMB cent.
+ out_trade_no: a unique order number generated manually and matches with you background.
+ user_id: payment user openid (required on official account payment)
+ product_id: required on NATIVE payment mode

For example:

```
http://wx.easecloud.cn/make_order/wx6426cb0a36327b31/?body=%E6%88%91%E4%BB%AC&total_fee=1&out_trade_no=SH2017011412042182
```

---

### V1.0 Old API usage:

Look into the *Entrance Link* below again:

```
https://open.weixin.qq.com/connect/oauth2/authorize
    ?appid=wx579e43a4729b1764
    &redirect_uri=http%3a%2f%2fwx.easecloud.cn
    &response_type=code
    &scope=snsapi_userinfo
    &state=ba0ab193
    #wechat_redirect
```

Focus on the querystring params:

1. **appid:** This is the appid of EaseCloud Inc, just use it;
2. **redirect_uri:** Our api sharing service url;
3. **response_type:** Just use 'code';
4. **scope:** Either 'snsapi_base' or 'snsapi_userinfo', see the api reference;
5. **state:** *Request target* and parameters;
6. **wechat_redirect:** Required, just use it;

##### Calling procedure (V1.0)

For example, we want to retrieve the user info in our website, the following
steps is require:

1. Register a request target in our service, you leave a callback uri, and then
   you got a 8-byte hex token which represents your callback uri.
   (The above `state=ba0ab193` is the token, for instance.)
2. Fill that token, in the entrance url, redirect the front-end user to that
   location. (You can also appends some characters as parameter on the `state`
   parameter, that string can send back to your callback later)
3. So the front-end user may or may not be prompt to allow you to collect
   his/her information (depends on the `scope` parameter).
4. Redirect to you registered request target uri, with two parameters in the
   querystring (openid and state).
5. With the given openid (identified the unique front-end wechat-user), you can
   retrieve his/her information by requesting
   `http://wx.easecloud.cn/user/{:openid}`, and do some logical judge on the
   source by the state parameter (the substring after the 8-byte token in your
   initial given state)

##### Detailed example (V1.0)

For example, if you have a php web page `http://example.com/login.php`, now you
want the user automatically signup and login when opened in wechat.

So now you register the uri `http://example.com/login.php` (for now you can
email to me <mailto:57082212@qq.com> in order to register)

We suppose your token is `1a2b3c4d`.

And you want to mark the user is from `login.php` by passing a state parameter
as `from_login`.

So you can construct an entrance url as below:

```
https://open.weixin.qq.com/connect/oauth2/authorize
    ?appid=wx579e43a4729b1764
    &redirect_uri=http%3a%2f%2fwx.easecloud.cn
    &response_type=code
    &scope=snsapi_userinfo
    &state=1a2b3c4dfrom_login
    #wechat_redirect
```

Now if the user visits the entrance, in you `login.php` code, you can retrieve
the `openid` of that user and the `state=from_login` parameter:

```php
<?php

$entrance_url =
    "https://open.weixin.qq.com/connect/oauth2/authorize".
    "?appid=wx579e43a4729b1764".
    "&redirect_uri=http%3a%2f%2fwx.easecloud.cn".
    "&response_type=code".
    "&scope=snsapi_userinfo".
    "&state=1a2b3c4dfrom_login".
    "#wechat_redirect";

// If visited in wechat, using the automatic login
if(preg_match('/MicroMessenger/', $_SERVER['HTTP_USER_AGENT'])) {
    $ticket = @$_GET['ticket'];
    // You can do some judge based on the $state parameter;
    $state = @$_GET['state'];  // you got 'from_login' here.
    if(!$ticket) {
        header('Location: '.$entrance_url);
        exit;
    }
    $user_info = json_decode(file_get_contents(
        "http://wx.easecloud.cn/ticket/$ticket/"
    ));
    // Implements your login/signup logic.
    login($user_info);
} else {
    // Ordinary login procedure...
}

```






