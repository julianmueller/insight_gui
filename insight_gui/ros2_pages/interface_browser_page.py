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

import subprocess

from rosidl_runtime_py import (
    get_message_interfaces,
    get_service_interfaces,
    get_action_interfaces,
    get_interface_path,
)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.msg_type_info_pages import (
    MessageTypeInfoPage,
    ServiceTypeInfoPage,
    ActionTypeInfoPage,
)
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow


class InterfaceBrowserPage(ContentPage):
    __gtype_name__ = "InterfaceBrowserPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Interface Browser")
        super().set_empty_page_text("Refresh to show interfaces")
        super().set_search_entry_placeholder_text("Search for interfaces")

    def on_realize(self, *args):
        super().on_realize(*args)

        # TODO make these buttons work
        btm_widgets = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"])
        super().add_bottom_widget(btm_widgets, position="center")
        btm_widgets.append(Gtk.ToggleButton(label="msgs", active=True))
        btm_widgets.append(Gtk.ToggleButton(label="srvs", active=True))
        btm_widgets.append(Gtk.ToggleButton(label="acts", active=True))

    def on_refresh_blocking(self) -> bool:
        self.available_msgs = get_message_interfaces()
        self.available_srvs = get_service_interfaces()
        self.available_action_msgs = get_action_interfaces()

        return len(self.available_msgs) + len(self.available_srvs) + len(self.available_action_msgs) > 0

    def on_refresh_gui(self):
        # add all the message interfaces
        for pkg_name, msgs_list in sorted(self.available_msgs.items()):
            msg_group = self.pref_page.add_group(title=pkg_name)

            msg_rows = []
            for msg in sorted(msgs_list):
                msg_type_full_name = f"{pkg_name}/{msg}"
                msg_type = msg.removeprefix("msg/")  # remove namespace

                # TODO add some kind of a label that a row is a message interface
                row = PrefRow(title=msg_type, subtitle=msg_type_full_name)
                # row.add_suffix_btn(
                #     icon_name="info-symbolic",
                #     tooltip_text="Message Info",
                #     func=self.on_get_msg_info,
                #     func_kwargs={"msg_type_full_name": msg_type_full_name},
                # )
                # row.add_suffix_btn(
                #     icon_name="folder-symbolic",
                #     tooltip_text="Open Message File",
                #     func=_on_open_msg_file,
                #     func_kwargs={"msg_type_full_name": msg_type_full_name},
                # )
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=MessageTypeInfoPage,
                    subpage_kwargs={"msg_type_full_name": msg_type_full_name},
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
                row = PrefRow(title=srv_type, subtitle=srv_type_full_name)
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=ServiceTypeInfoPage,
                    subpage_kwargs={"srv_type_full_name": srv_type_full_name},
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
                row = PrefRow(title=act_type, subtitle=act_type_full_name)
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=ActionTypeInfoPage,
                    subpage_kwargs={"act_type_full_name": act_type_full_name},
                )
                act_rows.append(row)
            actions_group.add_rows_idle(act_rows)

        if self.pref_page.num_groups == 0:
            self.pref_page.set_empty_page_text("No interfaces found. Refresh to try again.")

    def on_clear_gui(self):
        self.pref_page.clear()

    def on_interface_filters_changed(self, *args):
        print("not implemented yet")


# def _on_open_msg_file(btn: Gtk.Button = None, *, msg_type_full_name: str):
#     msg_file_path = get_interface_path(msg_type_full_name)
#     # i: ignore session
#     subprocess.Popen(["gnome-text-editor", msg_file_path, "--ignore-session"])
#     # os.system(f"gnome-text-editor {msg_file_path} -ins")
