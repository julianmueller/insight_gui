# =============================================================================
# interface_browser_page.py
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

from itertools import groupby

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.model_rows import InterfaceTypeRow


class InterfaceBrowserPage(ContentPage):
    __gtype_name__ = "InterfaceBrowserPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Interface Browser")
        super().set_placeholder_text("Refresh to show interfaces")
        super().set_search_entry_placeholder_text("Search for interfaces")

        # filter buttons for interface types
        btm_widgets = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"])
        super().add_bottom_widget(btm_widgets, position="center")

        # btn to show all interfaces
        self.filter_all_btn = Gtk.ToggleButton(
            label="all", active=True, width_request=100, tooltip_text="Show all interfaces"
        )
        self.filter_all_btn.connect("toggled", self.on_interface_filters_changed)
        btm_widgets.append(self.filter_all_btn)

        # btn to show only message interfaces
        self.filter_msgs_btn = Gtk.ToggleButton(
            label="msgs", active=False, width_request=100, tooltip_text="Show only message interfaces"
        )
        self.filter_msgs_btn.set_group(self.filter_all_btn)
        self.filter_msgs_btn.connect("toggled", self.on_interface_filters_changed)
        btm_widgets.append(self.filter_msgs_btn)

        # btn to show only service interfaces
        self.filter_srvs_btn = Gtk.ToggleButton(
            label="srvs", active=False, width_request=100, tooltip_text="Show only service interfaces"
        )
        self.filter_srvs_btn.set_group(self.filter_all_btn)
        self.filter_srvs_btn.connect("toggled", self.on_interface_filters_changed)
        btm_widgets.append(self.filter_srvs_btn)

        # btn to show only action interfaces
        self.filter_actions_btn = Gtk.ToggleButton(
            label="actions", active=False, width_request=100, tooltip_text="Show only action interfaces"
        )
        self.filter_actions_btn.set_group(self.filter_all_btn)
        self.filter_actions_btn.connect("toggled", self.on_interface_filters_changed)
        btm_widgets.append(self.filter_actions_btn)

        # add filter tags for all interface types
        # self.on_interface_filters_changed()

    def refresh_bg(self) -> bool:
        self.interfaces = [
            *self.ros2_connector.get_message_interfaces(),
            *self.ros2_connector.get_service_interfaces(),
            *self.ros2_connector.get_action_interfaces(),
        ]
        self.interfaces.sort(key=lambda interface: (interface.package, interface.interface_class, interface.name))
        self.interfaces_by_package = [
            (pkg_name, list(package_interfaces))
            for pkg_name, package_interfaces in groupby(self.interfaces, key=lambda interface: interface.package)
        ]

        return bool(self.interfaces)

    def refresh_ui(self):
        if not self.interfaces_by_package:
            self.pref_page.set_placeholder_text("No interfaces found. Refresh to try again.")
            return

        done = self._begin_refresh_job()
        package_iter = iter(self.interfaces_by_package)

        def add_package_groups():
            if not self._refreshing:
                return GLib.SOURCE_REMOVE

            for _ in range(1):
                try:
                    pkg_name, interfaces = next(package_iter)
                except StopIteration:
                    done()
                    return GLib.SOURCE_REMOVE

                group = self.pref_page.add_group(title=pkg_name, collapsable=True)
                self._add_item_rows_async(
                    group,
                    interfaces,
                    self._build_interface_row,
                    batch_size=16,
                    on_done=group.set_description_to_row_count,
                )

            return GLib.SOURCE_CONTINUE

        GLib.timeout_add(self._row_add_interval_ms, add_package_groups, priority=GLib.PRIORITY_LOW)

    def _build_interface_row(self, interface) -> InterfaceTypeRow:
        return InterfaceTypeRow(interface=interface, nav_view=self.nav_view)

    def reset_ui(self):
        self.pref_page.clear()

    def on_interface_filters_changed(self, btn: Gtk.ToggleButton, *args):
        self.add_conditional_filter_tag("msg", self.filter_msgs_btn.get_active())
        self.add_conditional_filter_tag("srv", self.filter_srvs_btn.get_active())
        self.add_conditional_filter_tag("action", self.filter_actions_btn.get_active())

        self.apply_filters()
