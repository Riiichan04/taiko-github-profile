"""Small SVG element and number helpers shared by vector components."""
from xml.etree.ElementTree import SubElement


def fmt(value):
    return format(value, '.8g')


def element(parent, tag, **attrs):
    return SubElement(parent, tag, {k.replace('_','-'):str(v) for k,v in attrs.items()})


