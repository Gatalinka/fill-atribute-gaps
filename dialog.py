# -*- coding: utf-8 -*-
"""
Fill Attribute Gaps — Dialog

A simple dialog with:
- Layer picker (all vector layers)
- Order-by field picker (numeric/integer fields)
- Target field picker (numeric fields to interpolate)
- Interpolation method radio buttons
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QRadioButton, QButtonGroup, QGroupBox,
    QDialogButtonBox, QLabel, QComboBox, QSpinBox,
)
from PyQt5.QtCore import Qt
from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox


class FillGapsDialog(QDialog):

    METHODS = [
        ("linear", "Linear", "Straight-line interpolation between key points"),
        ("nearest", "Nearest neighbor", "Copy the closest known value"),
        ("spline", "Cubic spline", "Smooth curve (may overshoot, needs 3+ keys)"),
        ("pchip", "PCHIP (smooth, no overshoot)", "Monotone cubic — never creates impossible values"),
        ("akima", "Akima (smooth transitions)", "Handles sharp changes without oscillation (needs 5+ keys)"),
        ("step", "Step (forward fill)", "Carry last known value forward"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fill Attribute Gaps")
        self.setMinimumWidth(380)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ── Layer / field pickers ───────────────────────────────
        form = QFormLayout()

        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        form.addRow("Layer:", self.layer_combo)

        self.order_combo = QComboBox()
        self.order_combo.addItem("— Feature order (row number) —", "")
        form.addRow("Order by:", self.order_combo)

        self.field_combo = QgsFieldComboBox()
        self.field_combo.setFilters(QgsFieldProxyModel.Numeric)
        form.addRow("Fill column:", self.field_combo)

        layout.addLayout(form)

        # Wire layer changes to field combos
        self.layer_combo.layerChanged.connect(self._update_order_fields)
        self.layer_combo.layerChanged.connect(self.field_combo.setLayer)

        # Initialize field combos with the current layer
        initial_layer = self.layer_combo.currentLayer()
        if initial_layer:
            self._update_order_fields(initial_layer)
            self.field_combo.setLayer(initial_layer)

        # ── Interpolation method ────────────────────────────────
        method_group = QGroupBox("Interpolation method")
        method_layout = QVBoxLayout()

        self.method_buttons = QButtonGroup(self)
        for i, (method_id, label, tooltip) in enumerate(self.METHODS):
            radio = QRadioButton(label)
            radio.setToolTip(tooltip)
            radio.setProperty("method_id", method_id)
            if i == 0:
                radio.setChecked(True)
            self.method_buttons.addButton(radio, i)
            method_layout.addWidget(radio)

        method_group.setLayout(method_layout)
        layout.addWidget(method_group)

        # ── Output precision ────────────────────────────────────
        precision_group = QGroupBox("Output precision")
        precision_layout = QVBoxLayout()

        self.precision_buttons = QButtonGroup(self)

        self.radio_auto = QRadioButton("Auto (match field type)")
        self.radio_auto.setToolTip(
            "Integer fields → round to whole numbers; "
            "decimal fields → keep full precision"
        )
        self.radio_auto.setChecked(True)
        self.precision_buttons.addButton(self.radio_auto, 0)
        precision_layout.addWidget(self.radio_auto)

        self.radio_integer = QRadioButton("Integer (round to whole numbers)")
        self.radio_integer.setToolTip("Always round results to the nearest integer")
        self.precision_buttons.addButton(self.radio_integer, 1)
        precision_layout.addWidget(self.radio_integer)

        # Decimal places row: radio + spinbox
        decimal_row = QHBoxLayout()
        self.radio_decimal = QRadioButton("Decimal places:")
        self.radio_decimal.setToolTip("Round results to a fixed number of decimal places")
        self.precision_buttons.addButton(self.radio_decimal, 2)
        decimal_row.addWidget(self.radio_decimal)

        self.decimal_spin = QSpinBox()
        self.decimal_spin.setRange(1, 10)
        self.decimal_spin.setValue(2)
        self.decimal_spin.setEnabled(False)
        self.decimal_spin.setFixedWidth(60)
        decimal_row.addWidget(self.decimal_spin)
        decimal_row.addStretch()
        precision_layout.addLayout(decimal_row)

        # Enable/disable spinbox based on radio selection
        self.precision_buttons.buttonClicked.connect(self._on_precision_changed)

        precision_group.setLayout(precision_layout)
        layout.addWidget(precision_group)

        # ── Info label ──────────────────────────────────────────
        info = QLabel("Only NULL cells are filled. Existing values (including 0) are kept.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-size: 10px; margin-top: 4px;")
        layout.addWidget(info)

        # ── Buttons ─────────────────────────────────────────────
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Fill Gaps")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Internal ──────────────────────────────────────────────────

    def _update_order_fields(self, layer):
        """Rebuild order-by dropdown when layer changes."""
        self.order_combo.clear()
        self.order_combo.addItem("— Feature order (row number) —", "")
        if layer:
            for field in layer.fields():
                if field.isNumeric():
                    self.order_combo.addItem(field.name(), field.name())

    def _on_precision_changed(self, button):
        """Enable the decimal spinbox only when 'Decimal places' is selected."""
        self.decimal_spin.setEnabled(button is self.radio_decimal)

    # ── Public getters ──────────────────────────────────────────

    def selected_layer(self):
        return self.layer_combo.currentLayer()

    def order_field(self):
        """Returns field name, or empty string for feature order."""
        return self.order_combo.currentData() or ""

    def target_field(self):
        return self.field_combo.currentField()

    def method(self):
        btn = self.method_buttons.checkedButton()
        return btn.property("method_id") if btn else "linear"

    def precision(self):
        """
        Returns the user's precision choice:
            "auto"    – match the target field type
            "integer" – round to whole numbers
            int(N)    – round to N decimal places
        """
        checked_id = self.precision_buttons.checkedId()
        if checked_id == 1:
            return "integer"
        elif checked_id == 2:
            return self.decimal_spin.value()
        else:
            return "auto"
