# =============================================================================
# preferences_dialog.py
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

import os
import webbrowser

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow
from insight_gui.widgets.buttons import PlayPauseButton

# TODO add setting to show/hide hidden nodes/topics etc


class PreferencesDialog(Adw.PreferencesDialog):
    __gtype_name__ = "PreferencesDialog"

    def __init__(self, ros2_connector: ROS2Connector, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Settings")

        self.ros2_connector = ros2_connector

    def on_realize(self, *args):
        # Page with ROS2 Settings
        self.ros2_page = PrefPage(title="ROS2", icon_name="applications-other-symbolic")
        super().add(self.ros2_page)

        # Group with ENV variables
        env_group = self.ros2_page.add_group(title="Environment Variables")
        env_group.add_suffix_btn(
            icon_name="info-symbolic",
            tooltip_text="ROS Documentation",
            func=lambda: webbrowser.open(
                "https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html#improveddynamicdiscovery"
            ),
        )

        self.env_auto_discovery_row = env_group.add_row(
            Adw.EntryRow(
                title="ROS_AUTOMATIC_DISCOVERY_RANGE",
                tooltip_text="choose between 'SUBNET', 'LOCALHOST', 'OFF', 'SYSTEM_DEFAULT'",
            )
        )
        self.env_static_peers_row = env_group.add_row(
            Adw.EntryRow(title="ROS_STATIC_PEERS", tooltip_text="list of IPs/domains, separated by ';'")
        )
        # self.env_static_peers_row.connect("notify::value")  # , lambda *_: self.on_static_peers_changed=True)
        self.env_domain_id_row = env_group.add_row(
            Adw.EntryRow(title="ROS_DOMAIN_ID", tooltip_text="unique number between 0 and 100")
        )
        self.env_discovery_server_row = env_group.add_row(Adw.EntryRow(title="ROS_DISCOVERY_SERVER", tooltip_text=""))
        self.env_apply_row = env_group.add_row(
            ButtonRow(
                label="Apply",
                tooltip_text="Apply Environment Variables",
                func=self.on_apply_env_vars,
            )
        )

        # Group for ROS2 Node Controls
        node_group = self.ros2_page.add_group(title="ROS2 Node")

        controls_row: PrefRow = node_group.add_row(PrefRow(title="Controls"))
        # controls_row.add_suffix(
        #     PlayPauseButton(tooltip_texts=("Start Node", "Stop Node"), func=self.on_toggle_ros2_node)
        # )
        start_btn = controls_row.add_suffix_btn(
            icon_name="media-playback-start-symbolic", tooltip_text="Start", func=lambda: None
        )
        start_btn.set_action_name("app.ros2_node_start")  # TODO not working
        stop_btn = controls_row.add_suffix_btn(
            icon_name="media-playback-stop-symbolic", tooltip_text="Stop", func=lambda: None
        )
        stop_btn.set_action_name("app.ros2_node_start")  # TODO not working

        # settings_group = self.ros2_page.add_group(title="Settings", description="bla")
        # row_node_name = settings_group.add_row(Adw.EntryRow(title="ros2_gui_node_name", show_apply_button=True))
        # row_hide_node = settings_group.add_row(Adw.SwitchRow(title="Hide Node"))
        # row_node_namespace = settings_group.add_row(Adw.EntryRow(title="ros2_connector_namespace", show_apply_button=True))
        # row_network_id = settings_group.add_row(Adw.EntryRow(title="ros2_network_id", show_apply_button=True))
        # row_apply_btn: PrefRow = settings_group.add_row(PrefRow(title="Apply Changes"))  # TODO make a ButtonRow
        # row_apply_btn.add_suffix_btn(
        #     icon_name="document-save-symbolic", tooltip_text="Save", func=self.on_apply_changes
        # )

        # row_apply_btn.connect("clicked", on_apply_changes)

        # self.page2 = PrefPage(title="Others", icon_name="applications-engineering-symbolic")
        # self.add(self.page2)

        # self.page2.add_group(title="Test", description="bla")

        # update env vars
        self.update_env_vars()

    def update_env_vars(self, *args):
        # TODO split loading of envs and widget text updating in two functions
        env_auto_discovery = os.getenv("ROS_AUTOMATIC_DISCOVERY_RANGE", default="")
        self.env_auto_discovery_row.set_text(env_auto_discovery)

        env_static_peers = os.getenv("ROS_STATIC_PEERS", default="")
        self.env_static_peers_row.set_text(env_static_peers)

        env_domain_id = os.getenv("ROS_DOMAIN_ID", default="")
        self.env_domain_id_row.set_text(env_domain_id)

        env_discovery_server = os.getenv("ROS_DISCOVERY_SERVER", default="")
        self.env_discovery_server_row.set_text(env_discovery_server)

    def on_apply_env_vars(self, *args):
        self.ros2_connector.stop_node()

        os.environ["ROS_AUTOMATIC_DISCOVERY_RANGE"] = self.env_auto_discovery_row.get_text()
        os.environ["ROS_STATIC_PEERS"] = self.env_static_peers_row.get_text()
        os.environ["ROS_DOMAIN_ID"] = self.env_domain_id_row.get_text()
        os.environ["ROS_DISCOVERY_SERVER"] = self.env_discovery_server_row.get_text()

        self.add_toast(Adw.Toast(title="Applied Environment Variables"))
        self.ros2_connector.start_node()

    def on_apply_changes(self, *args):
        is_running_str = "running" if self.ros2_connector.is_running else "not running"

        self.add_toast(Adw.Toast(title=f"ROS2 Node is {is_running_str}"))

    # def on_toggle_ros2_node(self, active: bool, *args):
    #     # self.get_application().lookup_action("ros2_node_is_running").get_state().get_boolean()
    #     if active:
    #         self.get_root().app.activate_action("ros2_node_stop", None)
    #         self.add_toast(Adw.Toast(title="Stopped ROS2 Node"))
    #     else:
    #         self.get_root().app.activate_action("ros2_node_start", None)
    #         self.add_toast(Adw.Toast(title="Started ROS2 Node"))
