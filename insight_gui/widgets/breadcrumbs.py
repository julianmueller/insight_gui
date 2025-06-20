# =============================================================================
# breadcrumbs.py
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
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio


class BreadcrumbsBar(Gtk.Frame):
    __gtype_name__ = "BreadcrumbsBar"

    def __init__(self, **kwargs):
        super().__init__(
            hexpand=True,
            vexpand=True,
            margin_top=6,
            margin_bottom=12,
            margin_start=12,
            margin_end=6,
        )

        # add horizontal scrolling (from a regular, vertical scroll)
        self.scrolled_window: Gtk.ScrolledWindow = Gtk.ScrolledWindow(
            # overlay_scrolling=False,
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC.NEVER,
        )
        self.scrolled_window.get_hscrollbar().set_can_target(False)  # this gets in the way

        scroll_controller = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll_controller.connect("scroll", self.on_scroll)
        self.scrolled_window.add_controller(scroll_controller)
        super().set_child(self.scrolled_window)

        self.box: Gtk.Box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=4, hexpand=True, halign=Gtk.Align.FILL
        )
        self.scrolled_window.set_child(self.box)

    def set_nav_view(self, nav_view: Adw.NavigationView):
        self.nav_view = nav_view

    def update(self, *args):
        if not self.nav_view:
            return

        # clear exisiting breadcrumbs
        self.clear()

        # build breadcrumbs from stack
        nav_stack: Gio.ListMode = self.nav_view.get_navigation_stack()
        num_pages = nav_stack.get_n_items()

        # hide when there are no subpages
        self.set_visible(num_pages > 1)

        for i in range(num_pages):
            page = nav_stack.get_item(i)
            bc_btn = BreadcrumbButton(nav_view=self.nav_view, nav_page=page)
            self.box.append(bc_btn)

            # add a separator label if not the last item
            if i < num_pages - 1:
                self.box.append(Gtk.Label(label=">"))

            else:
                # if this is the last item, make the label bold
                bc_btn.label.set_use_markup(True)
                bc_btn.set_label(f"<b>{bc_btn.label.get_text()}</b>")

        # scroll to the far right
        GLib.idle_add(self._scroll_to_right)

    def clear(self):
        child = self.box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.box.remove(child)
            child = next_child

    def on_scroll(self, controller, dx, dy) -> bool:
        hadj = self.scrolled_window.get_hadjustment()
        step = hadj.get_step_increment()
        # dy > 0 means wheel-down, so scroll right
        new_val = hadj.get_value() + dy * step

        # clamp within [lower, upper - page]
        lower = hadj.get_lower()
        upper = hadj.get_upper() - hadj.get_page_size()
        hadj.set_value(min(max(new_val, lower), upper))

        return True  # stop further handling

    def _scroll_to_right(self, *args):
        hadj = self.scrolled_window.get_hadjustment()
        # compute the absolute rightmost position
        max_pos = hadj.get_upper() - hadj.get_page_size()
        # clamp just in case
        hadj.set_value(max(0, max_pos))
        return False  # remove this idle handler


class BreadcrumbButton(Gtk.Button):
    __gtype_name__ = "BreadcrumbButton"

    def __init__(self, nav_view: Adw.NavigationView, nav_page: Adw.NavigationPage, **kwargs):
        super().__init__(**kwargs)
        self.nav_view = nav_view
        self.nav_page = nav_page

        page_title = self.nav_page.get_title()

        super().set_css_classes(["flat", "body"])
        super().set_label(page_title)
        super().set_tooltip_text(f"Go back to '{page_title}'")

        self.label = super().get_first_child()
        self.connect("clicked", self.on_click)

    def on_click(self, *args):
        self.nav_view.pop_to_page(self.nav_page)
