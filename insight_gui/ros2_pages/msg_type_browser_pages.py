# =============================================================================
# msg_type_browser_pages.py
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


class MessageTypeBrowserPage(ContentPage):
    __gtype_name__ = "MessageTypeBrowserPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Message Type Browser")
        super().set_empty_page_text("Refresh to show message types")
        super().set_search_entry_placeholder_text("Search for message types")

    def on_refresh_blocking(self) -> bool:
        self.available_msgs = get_message_interfaces()
        return len(self.available_msgs) > 0

    def on_refresh_gui(self):
        if len(self.available_msgs) == 0:
            self.pref_page.set_empty_page_text("No topics found. Refresh to try again.")

        for pkg_name, msgs_list in sorted(self.available_msgs.items()):
            msg_group = self.pref_page.add_group(title=pkg_name)

            for msg in sorted(msgs_list):
                msg_type_full_name = f"{pkg_name}/{msg}"
                msg_type = msg.removeprefix("msg/")  # remove namespace

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
                msg_group.add_row(row)

    def on_clear_gui(self):
        self.pref_page.clear()


class ServiceTypeBrowserPage(ContentPage):
    __gtype_name__ = "ServiceTypeBrowserPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Service Type Browser")
        super().set_empty_page_text("Refresh to show service types")
        super().set_search_entry_placeholder_text("Search for service types")

    def on_refresh_blocking(self) -> bool:
        self.available_srvs = get_service_interfaces()
        return len(self.available_srvs) > 0

    def on_refresh_gui(self):
        if len(self.available_srvs) == 0:
            self.pref_page.set_empty_page_text("No Services found. Refresh to try again.")

        for pkg_name, srvs_list in sorted(self.available_srvs.items()):
            srv_group = self.pref_page.add_group(title=pkg_name)

            for srv in sorted(srvs_list):
                srv_type_full_name = f"{pkg_name}/{srv}"
                srv_type = srv.removeprefix("srv/")  # remove namespace

                row = PrefRow(title=srv_type, subtitle=srv_type_full_name)
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=ServiceTypeInfoPage,
                    subpage_kwargs={"srv_type_full_name": srv_type_full_name},
                )
                srv_group.add_row(row)

    def on_clear_gui(self):
        self.pref_page.clear()


class ActionTypeBrowserPage(ContentPage):
    __gtype_name__ = "ActionTypeBrowserPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Action Type Browser")
        super().set_empty_page_text("Refresh to show action types")
        super().set_search_entry_placeholder_text("Search for action types")

    def on_refresh_blocking(self) -> bool:
        self.available_action_msgs = get_action_interfaces()
        return len(self.available_action_msgs) > 0

    def on_refresh_gui(self):
        if len(self.available_action_msgs) == 0:
            self.pref_page.set_empty_page_text("No actions found. Refresh to try again.")

        for pkg_name, actions_list in sorted(self.available_action_msgs.items()):
            actions_group = self.pref_page.add_group(title=pkg_name)

            for act in sorted(actions_list):
                act_type_full_name = f"{pkg_name}/{act}"
                act_type = act.removeprefix("msg/")  # remove namespace

                row = PrefRow(title=act_type, subtitle=act_type_full_name)

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
                    subpage_class=ActionTypeInfoPage,
                    subpage_kwargs={"act_type_full_name": act_type_full_name},
                )
                actions_group.add_row(row)

    def on_clear_gui(self):
        self.pref_page.clear()


def _on_open_msg_file(btn: Gtk.Button = None, *, msg_type_full_name: str):
    msg_file_path = get_interface_path(msg_type_full_name)
    # i: ignore session
    subprocess.Popen(["gnome-text-editor", msg_file_path, "--ignore-session"])
    # os.system(f"gnome-text-editor {msg_file_path} -ins")
