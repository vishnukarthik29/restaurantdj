from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """Build URL query string preserving existing GET params and overriding with kwargs."""
    request = context.get('request')
    params = request.GET.copy() if request else {}
    for k, v in kwargs.items():
        if v is None:
            params.pop(k, None)
        else:
            params[k] = str(v)
    qs = params.urlencode()
    return f'?{qs}' if qs else ''
