# =============================================================================
# adw_colors.py
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

from __future__ import annotations

# Adw supports accent colors with version 1.6, which is not available in ubuntu yet
# https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.6/enum.AccentColor.html

import random
from enum import StrEnum

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, Adw


class AdwAccentColor(StrEnum):
    ADW_ACCENT_COLOR_BLUE = "#3584e4"
    ADW_ACCENT_COLOR_TEAL = "#2190a4"
    ADW_ACCENT_COLOR_GREEN = "#3a944a"
    ADW_ACCENT_COLOR_YELLOW = "#c88800"
    ADW_ACCENT_COLOR_ORANGE = "#ed5b00"
    ADW_ACCENT_COLOR_RED = "#e62d42"
    ADW_ACCENT_COLOR_PINK = "#d56199"
    ADW_ACCENT_COLOR_PURPLE = "#9141ac"
    ADW_ACCENT_COLOR_SLATE = "#6f8396"

    def as_css_name(self) -> str:
        return self.name.lower().replace("_", "-")

    def as_css_style(self) -> str:
        return f"""
        .{self.as_css_name()} {{
            color: {get_contrast_text_color(self.value)};
            background-color: {self.value};
        }}
        """


def random_color() -> AdwAccentColor:
    return random.choice(list(AdwAccentColor))


def hex_to_rgba(color: AdwAccentColor) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    if rgba.parse(color):
        return rgba
    else:
        return None


# def get_luminance(hex_color):
#     color = hex_color[1:]

#     hex_red = int(color[0:2], base=16)
#     hex_green = int(color[2:4], base=16)
#     hex_blue = int(color[4:6], base=16)

#     return hex_red * 0.2126 + hex_green * 0.7152 + hex_blue * 0.0722


# see https://www.w3.org/TR/2008/REC-WCAG20-20081211/#relativeluminancedef
def get_contrast_text_color(bg_color: AdwAccentColor | str) -> str:
    rgba = hex_to_rgba(bg_color)

    def get_luminance(c: Gdk.RGBA):
        lum_r = c.red / 12.92 if c.red <= 0.03928 else ((c.red + 0.055) / 1.055) ** 2.4
        lum_g = c.green / 12.92 if c.green <= 0.03928 else ((c.green + 0.055) / 1.055) ** 2.4
        lum_b = c.blue / 12.92 if c.blue <= 0.03928 else ((c.blue + 0.055) / 1.055) ** 2.4
        return 0.2126 * lum_r + 0.7152 * lum_g + 0.0722 * lum_b

    # If the luminance is below 0.5, return True for dark, else False
    lum_bg = get_luminance(rgba)
    # lum_white = get_luminance(hex_to_rgba("#FFFFFF")) # lum = 1.0
    # lum_black = get_luminance(hex_to_rgba("#000000")) # lum = 0.0

    # If the luminance is below 0.5, return white, else black
    return "#FFFFFF" if lum_bg < 0.5 else "#000000"
