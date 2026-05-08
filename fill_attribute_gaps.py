# -*- coding: utf-8 -*-
"""
Fill Attribute Gaps — QGIS Plugin

Interpolate missing (NULL) attribute values between known key points.
Supports linear, nearest-neighbor, cubic spline, and step interpolation.
"""

import numpy as np
import os

from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QVariant
from qgis.core import NULL, Qgis

from .dialog import FillGapsDialog
from .interpolate import interpolate_gaps


class FillAttributeGaps:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.svg")
        self.action = QAction(
            QIcon(icon_path),
            "Fill Attribute Gaps",
            self.iface.mainWindow(),
        )
        self.action.setWhatsThis(
            "Interpolate missing attribute values between known key points"
        )
        self.action.setStatusTip(
            "Fill NULL values in a numeric field using interpolation"
        )
        self.action.triggered.connect(self.run)

        self.iface.addVectorToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu("&Fill Attribute Gaps", self.action)

    def unload(self):
        self.iface.removePluginVectorMenu("&Fill Attribute Gaps", self.action)
        self.iface.removeVectorToolBarIcon(self.action)

    def msg(self, text, level=Qgis.Warning):
        self.iface.messageBar().pushMessage("Fill Attribute Gaps", text, level, 8)

    def run(self):
        dlg = FillGapsDialog(self.iface.mainWindow())

        # Pre-select active layer if there is one
        active = self.iface.activeLayer()
        if active:
            dlg.layer_combo.setLayer(active)

        if not dlg.exec_():
            return

        # ── Read dialog selections ──────────────────────────────
        layer = dlg.selected_layer()
        order_field = dlg.order_field()
        target_field = dlg.target_field()
        method = dlg.method()
        precision = dlg.precision()

        if not layer:
            self.msg("No layer selected.")
            return
        if not target_field:
            self.msg("No target field selected.")
            return
        if layer.featureCount() == 0:
            self.msg("Layer has no features.")
            return

        # ── Load and sort features ──────────────────────────────
        features = list(layer.getFeatures())
        if order_field:
            # Sort by the chosen field
            features.sort(
                key=lambda f: f[order_field]
                if f[order_field] is not None and f[order_field] != NULL
                else 0
            )
        # else: keep feature order as-is (row number)
        n = len(features)
        feat_ids = [f.id() for f in features]

        # ── Read target values ──────────────────────────────────
        values = []
        is_null = []
        for f in features:
            v = f[target_field]
            if v is None or v == NULL or v == "":
                values.append(0.0)
                is_null.append(True)
            else:
                values.append(float(v))
                is_null.append(False)

        values = np.array(values)
        is_null = np.array(is_null)
        null_count = int(np.sum(is_null))
        key_count = int(np.sum(~is_null))

        if key_count == 0:
            self.msg("No key points found — all values are NULL. "
                     "Fill in some values first, then run again.")
            return
        if null_count == 0:
            self.msg("Nothing to fill — all values are already set.", Qgis.Info)
            return

        # ── Interpolate ────────────────────────────────────────
        new_values = interpolate_gaps(values, is_null, method)

        # ── Apply precision rounding ───────────────────────────
        if precision == "auto":
            field_type = layer.fields().field(target_field).type()
            if field_type in (QVariant.Int, QVariant.LongLong, QVariant.UInt,
                              QVariant.ULongLong):
                new_values = np.round(new_values, 0)
            # else: keep full float precision
        elif precision == "integer":
            new_values = np.round(new_values, 0)
        elif isinstance(precision, int):
            new_values = np.round(new_values, precision)

        # ── Apply changes with undo support ─────────────────────
        col_idx = layer.fields().indexOf(target_field)
        field_type = layer.fields().field(target_field).type()
        is_int_field = field_type in (QVariant.Int, QVariant.LongLong,
                                      QVariant.UInt, QVariant.ULongLong)

        layer.startEditing()
        layer.beginEditCommand(f"Fill Attribute Gaps ({method})")
        changed = 0
        for i, fid in enumerate(feat_ids):
            if is_null[i]:
                val = new_values[i]
                if is_int_field or precision == "integer":
                    val = int(round(val))
                else:
                    val = float(val)
                layer.changeAttributeValue(fid, col_idx, val)
                changed += 1
        layer.endEditCommand()
        layer.triggerRepaint()

        self.msg(
            f"Filled {changed} values using {method} interpolation. "
            f"Ctrl+Z to undo.",
            Qgis.Success,
        )
