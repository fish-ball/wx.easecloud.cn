def make_form(args, action, method='post', cls='payment-form'):
    html = "<meta http-equiv='content-type' content='text/html; charset=utf-8'>"
    html += '<form class="{}" action="{}" method="{}">'.format(cls, action, method)
    for k, v in args.items():
        html += '<div>{}<input name="{}" value="{}" /></div>'.format(k, k, v)
        # html += '<input type="hidden" name="{}" value="{}" />'.format(k, v)
    html += '<input type="submit">'
    html += '</form>'
    return html


def dict_to_url(args):
    return '&'.join(['{}={}'.format(k, v) for k, v in sorted(args.items())])
