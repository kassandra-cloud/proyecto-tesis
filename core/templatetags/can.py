# core/templatetags/can.py
from django import template
from core.authz import can   

register = template.Library()

@register.simple_tag(takes_context=True)
def user_can(context, resource: str, action: str) -> bool:
    """
    Uso en template:
        {% load can %}
        {% if user_can 'usuarios' 'view' %}
            ...
        {% endif %}
    """
    user = context["request"].user
    return can(user, resource, action)
