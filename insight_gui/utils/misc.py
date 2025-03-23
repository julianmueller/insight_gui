# =============================================================================
# misc.py
#
# This file is part of https://github.com/julianmueller/insight_gui
# Copyright (C) 2025 Julian Müller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
# =============================================================================


def is_between(value: float, lower: float, upper: float, incl_lower: bool = True, incl_upper: bool = True) -> bool:
    """
    Check if a value is in between a lower and an upper boundary. Whether the boundaries are included can be specified.

    :param value: value to check
    :param lower: lower boundary
    :param upper: upper boundary
    :param incl_lower: whether to include (<=) the lower boundary (vs exclude: <), defaults to True
    :param incl_upper: whether to include (>=) the upper boundary (vs exclude: >), defaults to True
    :return: whether the value is in between the boundary
    """
    if incl_lower:
        lower_check = lower <= value
    else:
        lower_check = lower < value

    if incl_upper:
        upper_check = value <= upper
    else:
        upper_check = value < upper

    return lower_check and upper_check


def clamp(value: float, lower: float, upper: float) -> float:
    """
    Clamp a value between two boundaries.

    :param value: number that will be clamped
    :param lower: lower boundary of the clamping
    :param upper: upper boundary of the clamping
    :return: clamped value
    """
    return max(lower, min(value, upper))
