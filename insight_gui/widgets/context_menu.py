# =============================================================================
# context_menu.py
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

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gio, Gdk, Adw, GLib


class ContextMenu:
    """Attach a small, programmable context menu to any widget."""

    def __init__(
        self,
        *,
        target: Gtk.Widget,
        action_prefix: str = "ctx",
        toast_overlay: Adw.ToastOverlay | None = None,
    ):
        self.target = target
        self.action_prefix = action_prefix
        self.toast_overlay = toast_overlay

        self._items: list[dict] = []
        self._popover = Gtk.PopoverMenu()
        self._popover.set_has_arrow(False)
        self._popover.set_parent(self.target)

        self._menu_model = Gio.Menu()
        self._popover.set_menu_model(self._menu_model)

        self._action_group = Gio.SimpleActionGroup()
        self.target.insert_action_group(self.action_prefix, self._action_group)

        # listen for right-clicks
        self._click_controller = Gtk.GestureClick()
        self._click_controller.set_button(Gdk.BUTTON_SECONDARY)
        self._click_controller.connect("released", self._on_button_released)
        self.target.add_controller(self._click_controller)

        # keyboard menu key support
        self._key_controller = Gtk.EventControllerKey()
        self._key_controller.connect("key-pressed", self._on_key_pressed)
        self.target.add_controller(self._key_controller)

    @property
    def has_items(self) -> bool:
        return any(item.get("type") != "separator" for item in self._items)

    @property
    def item_count(self) -> int:
        return len([item for item in self._items if item.get("type") != "separator"])

    def clear(self):
        """Remove all items from the menu."""
        self._items.clear()
        self._rebuild_menu()

    def add_separator(self, *, position: int | None = None):
        """Insert a visual separator."""
        insert_at = len(self._items) if position is None else max(0, position)
        before = self._items[insert_at - 1] if insert_at > 0 and insert_at - 1 < len(self._items) else None
        after = self._items[insert_at] if insert_at < len(self._items) else None
        if (before and before.get("type") == "separator") or (after and after.get("type") == "separator"):
            return
        self._items.insert(insert_at, {"type": "separator"})
        self._rebuild_menu()

    def upsert_item(
        self,
        action_id: str,
        label: str,
        callback: Callable,
        *,
        icon_name: str = "",
        position: int | None = None,
    ):
        """Add or replace an item identified by action_id."""
        self._items = [item for item in self._items if item.get("id") != action_id]
        insert_at = len(self._items) if position is None else max(0, position)
        self._items.insert(
            insert_at,
            {
                "id": action_id,
                "label": label,
                "callback": callback,
                "icon_name": icon_name,
            },
        )
        self._rebuild_menu()

    def _rebuild_menu(self):
        self._menu_model.remove_all()
        for name in self._action_group.list_actions():
            self._action_group.remove_action(name)

        section = Gio.Menu()
        for item in self._items:
            if item.get("type") == "separator":
                if section.get_n_items() > 0:
                    self._menu_model.append_section(None, section)
                    section = Gio.Menu()
                continue

            action = Gio.SimpleAction.new(item["id"], None)
            action.connect("activate", lambda _action, _param, cb=item["callback"]: cb())
            self._action_group.add_action(action)

            menu_item = Gio.MenuItem.new(item["label"], f"{self.action_prefix}.{item['id']}")
            if item.get("icon_name"):
                menu_item.set_icon(Gio.ThemedIcon.new(item["icon_name"]))
            section.append_item(menu_item)

        if section.get_n_items() > 0:
            self._menu_model.append_section(None, section)

        self._popover.set_menu_model(self._menu_model)

    def popup(self, x: float | None = None, y: float | None = None):
        """Show the popover at the given coordinates (widget-relative)."""
        if not self.has_items:
            return

        allocation = self.target.get_allocation()
        rect = Gdk.Rectangle()
        rect.x = int(x if x is not None else allocation.width / 2)
        rect.y = int(y if y is not None else allocation.height / 2)
        rect.width = 1
        rect.height = 1

        self._popover.set_pointing_to(rect)
        self._popover.popup()

    def _show_toast(self, text: str):
        overlay = self.toast_overlay or self.target.get_ancestor(Adw.ToastOverlay)
        if overlay:
            overlay.add_toast(Adw.Toast(title=text))

    def _on_button_released(self, controller: Gtk.GestureClick, n_press: int, x: float, y: float):
        if controller.get_current_button() != Gdk.BUTTON_SECONDARY:
            return

        def _popup_after_click():
            if self._popover.get_visible():
                self._popover.popdown()
            self.popup(x, y)
            return GLib.SOURCE_REMOVE

        GLib.idle_add(_popup_after_click, priority=GLib.PRIORITY_DEFAULT_IDLE)

    def _on_key_pressed(self, _controller, keyval: int, _keycode: int, state: Gdk.ModifierType):
        if keyval == Gdk.KEY_Menu or (keyval == Gdk.KEY_F10 and state & Gdk.ModifierType.SHIFT_MASK):
            self.popup()
            return True
        return False
