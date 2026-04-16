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

from rosidl_runtime_py import (
    get_message_interfaces,
    get_service_interfaces,
    get_action_interfaces,
)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow


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
        self.available_msgs = get_message_interfaces()
        self.available_srvs = get_service_interfaces()
        self.available_action_msgs = get_action_interfaces()

        return len(self.available_msgs) + len(self.available_srvs) + len(self.available_action_msgs) > 0

    def refresh_ui(self):
        # add all the message interfaces
        for pkg_name, msgs_list in sorted(self.available_msgs.items()):
            msg_group = self.pref_page.add_group(title=pkg_name)
            self._add_item_rows_async(
                msg_group,
                sorted(msgs_list),
                lambda msg, pkg_name=pkg_name: self._build_interface_row(pkg_name, msg, "msg"),
                batch_size=20,
            )

        # add all the service interfaces
        for pkg_name, srvs_list in sorted(self.available_srvs.items()):
            srv_group = self.pref_page.add_group(title=pkg_name)
            self._add_item_rows_async(
                srv_group,
                sorted(srvs_list),
                lambda srv, pkg_name=pkg_name: self._build_interface_row(pkg_name, srv, "srv"),
                batch_size=20,
            )

        # add all the action interfaces
        for pkg_name, actions_list in sorted(self.available_action_msgs.items()):
            actions_group = self.pref_page.add_group(title=pkg_name)
            self._add_item_rows_async(
                actions_group,
                sorted(actions_list),
                lambda action, pkg_name=pkg_name: self._build_interface_row(pkg_name, action, "action"),
                batch_size=20,
            )

        # sort the groups alphabetically by title
        self.pref_page.sort_groups()

        if self.pref_page.num_groups == 0:
            self.pref_page.set_placeholder_text("No interfaces found. Refresh to try again.")

    def _build_interface_row(self, pkg_name: str, interface_name: str, interface_tag: str) -> PrefRow:
        interface_full_name = f"{pkg_name}/{interface_name}"
        row = PrefRow(
            title=interface_name.removeprefix("msg/").removeprefix("srv/").removeprefix("action/"),
            subtitle=interface_full_name,
            tags=[interface_tag],
        )
        row.set_subpage_link(
            nav_view=self.nav_view,
            subpage_class=InterfaceInfoPage,
            subpage_kwargs={"interface_full_name": interface_full_name},
        )
        return row

    def reset_ui(self):
        self.pref_page.clear()

    def on_interface_filters_changed(self, btn: Gtk.ToggleButton, *args):
        self.add_conditional_filter_tag("msg", self.filter_msgs_btn.get_active())
        self.add_conditional_filter_tag("srv", self.filter_srvs_btn.get_active())
        self.add_conditional_filter_tag("action", self.filter_actions_btn.get_active())

        self.apply_filters()
