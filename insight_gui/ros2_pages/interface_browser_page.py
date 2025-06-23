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
        super().set_empty_page_text("Refresh to show interfaces")
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

            msg_rows = []
            for msg in sorted(msgs_list):
                msg_type_full_name = f"{pkg_name}/{msg}"
                msg_type = msg.removeprefix("msg/")  # remove namespace

                row = PrefRow(title=msg_type, subtitle=msg_type_full_name, tags=["msg"])
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=InterfaceInfoPage,
                    subpage_kwargs={"interface_full_name": msg_type_full_name},
                )
                msg_rows.append(row)
            msg_group.add_rows_idle(msg_rows)

        # add all the service interfaces
        for pkg_name, srvs_list in sorted(self.available_srvs.items()):
            srv_group = self.pref_page.add_group(title=pkg_name)

            srv_rows = []
            for srv in sorted(srvs_list):
                srv_type_full_name = f"{pkg_name}/{srv}"
                srv_type = srv.removeprefix("srv/")  # remove namespace

                # TODO add some kind of a label that a row is a service interface
                row = PrefRow(title=srv_type, subtitle=srv_type_full_name, tags=["srv"])
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=InterfaceInfoPage,
                    subpage_kwargs={"interface_full_name": srv_type_full_name},
                )
                srv_rows.append(row)
            srv_group.add_rows_idle(srv_rows)

        # add all the action interfaces
        for pkg_name, actions_list in sorted(self.available_action_msgs.items()):
            actions_group = self.pref_page.add_group(title=pkg_name)

            act_rows = []
            for act in sorted(actions_list):
                act_type_full_name = f"{pkg_name}/{act}"
                act_type = act.removeprefix("msg/")  # remove namespace

                # TODO add some kind of a label that a row is an action interface
                row = PrefRow(title=act_type, subtitle=act_type_full_name, tags=["action"])
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=InterfaceInfoPage,
                    subpage_kwargs={"interface_full_name": act_type_full_name},
                )
                act_rows.append(row)
            actions_group.add_rows_idle(act_rows)

        # sort the groups alphabetically by title
        self.pref_page.sort_groups()

        if self.pref_page.num_groups == 0:
            self.pref_page.set_empty_page_text("No interfaces found. Refresh to try again.")

    def reset_ui(self):
        self.pref_page.clear()

    def on_interface_filters_changed(self, btn: Gtk.ToggleButton, *args):
        self.add_conditional_filter_tag("msg", self.filter_msgs_btn.get_active())
        self.add_conditional_filter_tag("srv", self.filter_srvs_btn.get_active())
        self.add_conditional_filter_tag("action", self.filter_actions_btn.get_active())

        self.reapply_filters()
