# -*- coding: utf-8 -*-
"""
Core interpolation logic — six methods for filling NULL gaps
in a numeric attribute sequence.
"""

import numpy as np


def interpolate_gaps(values, is_null, method="linear"):
    """
    Fill NULL positions in *values* by interpolating from non-NULL key points.

    Parameters
    ----------
    values : np.ndarray   – full value array (NULLs can be any number, they're ignored)
    is_null : np.ndarray  – boolean mask, True where value should be filled
    method : str          – "linear", "nearest", "spline", "pchip", "akima", or "step"

    Returns
    -------
    np.ndarray – copy of *values* with NULLs replaced by interpolated values
    """
    result = values.copy()
    key_idx = np.where(~is_null)[0]

    if len(key_idx) == 0:
        return result  # nothing to interpolate from
    if not np.any(is_null):
        return result  # nothing to fill

    dispatch = {
        "linear":  _linear,
        "nearest": _nearest,
        "spline":  _spline,
        "pchip":   _pchip,
        "akima":   _akima,
        "step":    _step,
    }
    fn = dispatch.get(method, _linear)
    result = fn(values, is_null, key_idx)

    return result.astype(float)


# ── Linear ──────────────────────────────────────────────────────────

def _linear(values, is_null, key_idx):
    """Piecewise linear interpolation; constant extrapolation at edges."""
    key_vals = values[key_idx]
    all_idx = np.arange(len(values))
    result = np.interp(all_idx, key_idx, key_vals)
    result[~is_null] = values[~is_null]
    return result


# ── Nearest neighbor ────────────────────────────────────────────────

def _nearest(values, is_null, key_idx):
    """Each NULL gets the value of the nearest non-NULL by index distance."""
    result = values.copy()
    null_positions = np.where(is_null)[0]

    for pos in null_positions:
        distances = np.abs(key_idx - pos)
        nearest = key_idx[np.argmin(distances)]
        result[pos] = values[nearest]

    return result


# ── Cubic spline ────────────────────────────────────────────────────

def _spline(values, is_null, key_idx):
    """
    Cubic spline through key points. Can overshoot — use PCHIP if
    you need monotone behavior. Falls back to linear if scipy
    is unavailable or fewer than 3 key points.
    """
    if len(key_idx) < 3:
        return _linear(values, is_null, key_idx)

    try:
        from scipy.interpolate import CubicSpline
        key_vals = values[key_idx]
        cs = CubicSpline(key_idx.astype(float), key_vals, bc_type="clamped")

        result = values.copy()
        null_positions = np.where(is_null)[0]
        result[null_positions] = cs(null_positions.astype(float))
        return result

    except ImportError:
        return _linear(values, is_null, key_idx)


# ── PCHIP (monotone, no overshoot) ─────────────────────────────────

def _pchip(values, is_null, key_idx):
    """
    Piecewise Cubic Hermite Interpolating Polynomial.
    Smooth like spline but preserves monotonicity — never overshoots.
    Best for elevation profiles where you don't want impossible values.
    Falls back to linear if scipy unavailable or fewer than 3 key points.
    """
    if len(key_idx) < 3:
        return _linear(values, is_null, key_idx)

    try:
        from scipy.interpolate import PchipInterpolator
        key_vals = values[key_idx]
        pchip = PchipInterpolator(key_idx.astype(float), key_vals, extrapolate=False)

        result = values.copy()
        null_positions = np.where(is_null)[0]
        interp_vals = pchip(null_positions.astype(float))

        # Handle NaN at edges (where extrapolate=False returns NaN)
        nan_mask = np.isnan(interp_vals)
        if np.any(nan_mask):
            # Fill edges with nearest key value
            edge_result = _linear(values, is_null, key_idx)
            interp_vals[nan_mask] = edge_result[null_positions[nan_mask]]

        result[null_positions] = interp_vals
        return result

    except ImportError:
        return _linear(values, is_null, key_idx)


# ── Akima (smooth, handles sharp transitions) ──────────────────────

def _akima(values, is_null, key_idx):
    """
    Akima spline — smooth interpolation that handles sharp transitions
    without wild oscillations. Needs 5+ key points for best results.
    Falls back to PCHIP with fewer points, or linear without scipy.
    """
    if len(key_idx) < 5:
        return _pchip(values, is_null, key_idx)

    try:
        from scipy.interpolate import Akima1DInterpolator
        key_vals = values[key_idx]
        akima = Akima1DInterpolator(key_idx.astype(float), key_vals)

        result = values.copy()
        null_positions = np.where(is_null)[0]
        interp_vals = akima(null_positions.astype(float))

        # Handle NaN at edges
        nan_mask = np.isnan(interp_vals)
        if np.any(nan_mask):
            edge_result = _linear(values, is_null, key_idx)
            interp_vals[nan_mask] = edge_result[null_positions[nan_mask]]

        result[null_positions] = interp_vals
        return result

    except ImportError:
        return _linear(values, is_null, key_idx)


# ── Step (forward fill) ────────────────────────────────────────────

def _step(values, is_null, key_idx):
    """
    Each NULL takes the value of the most recent non-NULL before it.
    Leading NULLs (before any key point) get the first known value.
    """
    result = values.copy()

    last_known = values[key_idx[0]]
    for i in range(len(values)):
        if not is_null[i]:
            last_known = values[i]
        else:
            result[i] = last_known

    first_key = key_idx[0]
    if first_key > 0:
        result[:first_key] = values[first_key]

    return result
