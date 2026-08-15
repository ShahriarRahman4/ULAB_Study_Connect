from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from chatbot.engine import markdown_to_html

register = template.Library()


@register.filter
def nova_md(value):
    return mark_safe(markdown_to_html(value or ""))


@register.filter
def nova_plain(value):
    return mark_safe(escape(value or "").replace("\n", "<br>"))
