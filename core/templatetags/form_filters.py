# core/templatetags/form_filters.py
from django import template

register = template.Library()

@register.filter
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})

@register.filter
def placeholder(field, text):
    return field.as_widget(attrs={"placeholder": text})

@register.filter
def is_checkbox(field):
    return field.field.widget.__class__.__name__ == "CheckboxInput"

@register.filter
def is_radio(field):
    return field.field.widget.__class__.__name__ == "RadioSelect"