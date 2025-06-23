# =============================================================================
# gtk_utils.py
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

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio


# same order as with css margins
# https://developer.mozilla.org/en-US/docs/Web/CSS/margin#syntax
def set_margin(widget: Gtk.Widget, margin: list | int):
    """
    Set the margins of a GTK.Widget using a list.

    Options:
        - one value for all
        - 2x list: [top & bottom, right=end & left=start]
        - 3x list: [top, right=end & left=start, bottom]
        - 4x list: [top, right=end, bottom, left=start]
    """
    m = margins_dict(margin)
    for k, v in m.items():
        widget.set_property(k, v)


def margins_dict(margin: list | int):
    """
    Set the margins of a GTK.Widget using a dict.

    Options:
        - one value for all
        - 2x list: [top & bottom, right=end & left=start]
        - 3x list: [top, right=end & left=start, bottom]
        - 4x list: [top, right=end, bottom, left=start]
    """
    if isinstance(margin, list) and len(margin) == 2:
        margin_top = margin[0]
        margin_bottom = margin[0]
        margin_end = margin[1]
        margin_start = margin[1]
    elif isinstance(margin, list) and len(margin) == 3:
        margin_top = margin[0]
        margin_end = margin[1]
        margin_start = margin[1]
        margin_bottom = margin[2]
    elif isinstance(margin, list) and len(margin) == 4:
        margin_top = margin[0]
        margin_end = margin[1]
        margin_bottom = margin[2]
        margin_start = margin[3]
    elif isinstance(margin, int):
        margin_top = margin
        margin_end = margin
        margin_bottom = margin
        margin_start = margin
    else:
        raise ValueError("malformatted margins")

    return {
        "margin_top": margin_top,
        "margin_end": margin_end,
        "margin_bottom": margin_bottom,
        "margin_start": margin_start,
    }


def add_css_classes(widget: Gtk.Widget, classes: list):
    """Add multiple css classes to a GTK.Widget."""
    if not isinstance(widget, list):
        raise ValueError("malformatted css classes")

    for _class in classes:
        widget.add_css_class(_class)


# rather use: success, pos = list_store.find(Gtk.StringObject.new(string)
def find_str_in_list_store(list_store: Gio.ListStore, string: str) -> int:
    """Find a string in a Gio.ListStore and return its index (-1 when not found)."""
    for i, item in enumerate(list_store):
        if item.get_string() == string:
            return i
    else:
        return -1


# TODO test and adopt this
def copy_text_to_clipboard(text: str):
    clip = Gtk.Clipboard.get(Gio.Application.get_default())
    clip.set_text(text)


def get_child_by_name(parent_widget, name):
    """Get the child of a GTK.Widget by its name."""
    first_child = parent_widget.get_first_child()
    last_child = parent_widget.get_last_child()

    # Iterate through siblings until the name matches or no more children exist
    child = first_child
    while child:
        if child.get_name() == name:
            return child
        # If we reach the last child and it's not the target, break out
        if child == last_child:
            break
        child = child.get_next_sibling()

    return None


def get_children(widget) -> list:
    first_child = widget.get_first_child()
    last_child = widget.get_last_child()
    children = []

    # Iterate through siblings until the name matches or no more children exist
    child = first_child
    while child:
        children.append(child)
        # If we reach the last child and it's not the target, break out
        if child == last_child:
            break
        child = child.get_next_sibling()

    return children
