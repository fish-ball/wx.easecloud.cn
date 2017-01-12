WeChat SNS API shared by Easecloud Co. Ltd.
===========================================

### API documentation reference:

<https://mp.weixin.qq.com/wiki?t=resource/res_main&id=mp1421140842&token=&lang=zh_CN>

Minimal Example
---------------

Open the link below in the WeChat browser:

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

### Calling procedure

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

### Detailed example

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






