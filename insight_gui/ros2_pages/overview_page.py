# =============================================================================
# overview_page.py
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

import re
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, Gdk, Pango

from insight_gui.widgets.content_page import ContentPage
from insight_gui.pages import Page


class PageCard(Gtk.Button):
    __gtype_name__ = "PageCard"

    page = GObject.Property(type=object)

    def __init__(self, page: Page, **kwargs):
        super().__init__(**kwargs)
        super().set_size_request(150, 100)
        super().set_valign(Gtk.Align.FILL)
        super().set_halign(Gtk.Align.FILL)
        super().add_css_class("card")

        self.page: Page = page

        # Create the card content
        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=16,
            margin_start=16,
            margin_end=16,
            margin_top=12,
            margin_bottom=12,
        )
        super().set_child(box)

        # Icon
        icon = Gtk.Image(icon_name=self.page.icon_name, pixel_size=48, css_classes=["accent"])
        box.append(icon)

        # Text content
        text_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER, vexpand=True, hexpand=True
        )
        box.append(text_box)

        title_lbl = Gtk.Label(
            label=self.page.title,
            halign=Gtk.Align.FILL,
            hexpand=True,
            xalign=0.0,
            max_width_chars=12,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            css_classes=["heading"],
        )
        text_box.append(title_lbl)

        subtitle_lbl = Gtk.Label(
            label=self.page.subtitle,
            halign=Gtk.Align.FILL,
            hexpand=True,
            xalign=0.0,
            max_width_chars=12,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            css_classes=["dim-label"],
        )
        text_box.append(subtitle_lbl)

    def matches_search(self, search_text: str) -> bool:
        """Check if this card matches the search text"""
        if not search_text:
            return True

        return re.search(search_text, f"{self.page.title} {self.page.subtitle}", re.IGNORECASE)


class OverviewPage(ContentPage):
    __gtype_name__ = "OverviewPage"

    def __init__(self, page_groups=None, **kwargs):
        super().__init__(refreshable=False, searchable=True, detachable=False, **kwargs)
        super().set_title("Overview")
        super().set_search_entry_placeholder_text("Search pages...")

        self.page_groups = page_groups or []
        self.cards = []

        # Create scrolled window for the main content
        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER, vscrollbar_policy=Gtk.PolicyType.AUTOMATIC, vexpand=True
        )
        self.content_stack.add_child(scrolled)
        self.content_stack.set_visible_child(scrolled)

        # Cards container for this group
        self.cards_flowbox = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            max_children_per_line=6,
            min_children_per_line=1,
            column_spacing=8,
            row_spacing=8,
            homogeneous=True,
            valign=Gtk.Align.START,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=12,
        )
        scrolled.set_child(self.cards_flowbox)

        # Create groups and cards from page_groups
        for page_group in self.page_groups:
            for page in page_group.pages:
                card = PageCard(page)

                # Add gesture for Ctrl+click to open in detached window
                gesture = Gtk.GestureClick()
                gesture.connect("pressed", self.on_card_gesture, page.page_id)
                card.add_controller(gesture)

                self.cards_flowbox.append(card)
                self.cards.append(card)

    def on_card_clicked(self, card: PageCard, page_id: str):
        # Get the main window and navigate to the page
        window = self.app.main_window
        nav_view = window.content_stack.get_child_by_name(page_id)
        window.content_stack.set_visible_child(nav_view)

    def on_card_gesture(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float, page_id: str):
        state = gesture.get_current_event_state()
        window = self.app.main_window
        nav_view = window.content_stack.get_child_by_name(page_id)
        page = nav_view.get_visible_page()

        # Ctrl+click - open in detached window
        if state & Gdk.ModifierType.CONTROL_MASK:
            page.detach()
        else:
            window.content_stack.set_visible_child(nav_view)

    def on_search_changed(self, *args):
        search_text = self.search_entry.get_text()

        for card in self.cards:
            visible_cards = 0

            if card.matches_search(search_text):
                card.get_parent().set_visible(True)
                visible_cards += 1
            else:
                card.get_parent().set_visible(False)
