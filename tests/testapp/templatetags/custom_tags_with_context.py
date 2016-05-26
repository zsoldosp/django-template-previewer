from django import template
register = template.Library()


@register.simple_tag(takes_context=True)
def get_a_context_val(context, var_name, *var_properties_used):
    var = context[var_name]
    for prop_name in var_properties_used:
        var = getattr(var, prop_name)
    return str(var)

