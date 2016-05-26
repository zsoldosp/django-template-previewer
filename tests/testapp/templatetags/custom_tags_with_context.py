from django import template
register = template.Library()


@register.simple_tag(takes_context=True)
def get_a_context_val(context, var_name):
    return str(context[var_name])

