from django import template
register = template.Library()

@register.filter
def get_item(obj, key):
    return obj.get(key, "")
