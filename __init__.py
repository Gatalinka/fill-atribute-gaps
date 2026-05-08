# -*- coding: utf-8 -*-
def classFactory(iface):
    from .fill_attribute_gaps import FillAttributeGaps
    return FillAttributeGaps(iface)
