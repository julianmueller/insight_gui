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
from pathlib import Path

from rclpy.validate_node_name import validate_node_name
from rclpy.validate_namespace import validate_namespace
from rclpy.exceptions import InvalidNodeNameException, InvalidNamespaceException

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow
from insight_gui.widgets.buttons import PlayPauseButton


class PreferencesDialog(Adw.PreferencesDialog):
    __gtype_name__ = "PreferencesDialog"

    def __init__(self, ros2_connector: ROS2Connector, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Settings")
        super().set_size_request(400, 600)
        super().connect("close-attempt", self.on_close_attempt)
        GLib.idle_add(self._deferred_init)

        self.ros2_connector = ros2_connector

    def _deferred_init(self):
        self.app = self.get_root().app

        # Create ROS2 connection and environment settings page
        self.ros2_page = PrefPage(title="ROS2", icon_name="network-proxy-symbolic")
        super().add(self.ros2_page)

        # Environment Variables Group
        env_group = self.ros2_page.add_group(title="Environment Variables")
        env_group.add_suffix_btn(
            icon_name="update-symbolic", tooltip_text="Refresh Environment Variables", func=self.update_env_vars
        )
        env_group.add_suffix_btn(
            icon_name="info-symbolic",
            tooltip_text="ROS Documentation",
            func=lambda: Gio.AppInfo.launch_default_for_uri(
                "https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html#improveddynamicdiscovery",
                None,
            ),
        )

        self.env_domain_id_row = env_group.add_row(
            Adw.EntryRow(
                title="ROS_DOMAIN_ID",
                tooltip_text="unique number between 0 and 100",
                show_apply_button=True,
            )
        )
        self.env_domain_id_row.connect("apply", self.on_apply_env_var, "ROS_DOMAIN_ID")

        self.env_auto_discovery_row = env_group.add_row(
            Adw.EntryRow(
                title="ROS_AUTOMATIC_DISCOVERY_RANGE",
                tooltip_text="choose between 'SUBNET', 'LOCALHOST', 'OFF', 'SYSTEM_DEFAULT'",
                show_apply_button=True,
            )
        )
        self.env_auto_discovery_row.connect("apply", self.on_apply_env_var, "ROS_AUTOMATIC_DISCOVERY_RANGE")

        self.env_static_peers_row = env_group.add_row(
            Adw.EntryRow(
                title="ROS_STATIC_PEERS",
                tooltip_text="list of IPs/domains, separated by ';'",
                show_apply_button=True,
            )
        )
        self.env_static_peers_row.connect("apply", self.on_apply_env_var, "ROS_STATIC_PEERS")
        self.env_discovery_server_row = env_group.add_row(
            Adw.EntryRow(
                title="ROS_DISCOVERY_SERVER",
                tooltip_text="",
                show_apply_button=True,
            )
        )
        self.env_discovery_server_row.connect("apply", self.on_apply_env_var, "ROS_DISCOVERY_SERVER")

        # Update environment variables from current environment
        self.update_env_vars()

        # self.env_apply_row = env_group.add_row(
        #     ButtonRow(
        #         label="Apply Environment Variables",
        #         tooltip_text="Apply Environment Variables and restart ROS2 node",
        #         func=self.on_apply_env_vars,
        #     )
        # )

        # ROS2 Node Control Group
        gui_node_group = self.ros2_page.add_group(title="GUI Node Control")

        is_running_action = self.app.lookup_action("ros2-node-is-running")
        is_running = is_running_action.get_state().get_boolean()
        self.controls_row: PrefRow = gui_node_group.add_row(
            PrefRow(title="GUI Node Status", subtitle=f"ROS2 Node is {'running' if is_running else 'not running'}")
        )
        self.controls_row.add_suffix(
            PlayPauseButton(
                tooltip_texts=("Start Node", "Stop Node"),
                func=self.on_toggle_ros2_node,
                default_active=True,
                vexpand=False,
                valign=Gtk.Align.CENTER,
            )
        )
        self.node_state_changed_handler = is_running_action.connect("notify::state", self.on_change_node_running_state)

        self.auto_start_gui_node_row = gui_node_group.add_row(
            Adw.SwitchRow(
                title="Auto-start GUI Node",
                subtitle="Automatically start the ROS2 node for the GUI when its started",
                active=True,
            )
        )
        self.app.settings.bind(
            "auto-start-gui-node", self.auto_start_gui_node_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        # Node Configuration Group
        gui_node_config_group = self.ros2_page.add_group(title="Node Configuration")

        self.gui_node_name_row = gui_node_config_group.add_row(
            Adw.EntryRow(
                title="GUI-Node Name",
                text="insight_gui",
                tooltip_text="Name of the ROS2 node created by Insight GUI",
                show_apply_button=True,
            )
        )
        self.gui_node_name_row.connect("apply", self.on_apply_gui_node_name)
        self.app.settings.bind("gui-node-name", self.gui_node_name_row, "text", Gio.SettingsBindFlags.DEFAULT)

        self.gui_node_namespace_row = gui_node_config_group.add_row(
            Adw.EntryRow(
                title="GUI-Node Namespace",
                text="",
                tooltip_text="Namespace for the ROS2 GUI-Node (leave empty for root namespace)",
                show_apply_button=True,
            )
        )
        self.gui_node_namespace_row.connect("apply", self.on_apply_gui_node_namespace)
        self.app.settings.bind("gui-node-namespace", self.gui_node_namespace_row, "text", Gio.SettingsBindFlags.DEFAULT)

        ########### DISPLAY PAGE ###########

        self.display_page = PrefPage(title="Display", icon_name="preferences-desktop-display-symbolic")
        super().add(self.display_page)

        # Node Options
        node_options_group = self.display_page.add_group(
            title="Nodes Options", description="Configure how nodes are displayed and organized"
        )

        self.group_nodes_by_namespace_row = node_options_group.add_row(
            Adw.SwitchRow(
                title="Group Nodes by Namespace",
                subtitle="Organize nodes by their namespace",
                active=True,
            )
        )
        self.app.settings.bind(
            "group-nodes-by-namespace", self.group_nodes_by_namespace_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        self.show_hidden_nodes_row = node_options_group.add_row(
            Adw.SwitchRow(
                title="Show Hidden Nodes",
                subtitle="Display nodes with names starting with underscore",
                active=False,
            )
        )
        self.app.settings.bind("show-hidden-nodes", self.show_hidden_nodes_row, "active", Gio.SettingsBindFlags.DEFAULT)

        # Topic Options
        topic_options_group = self.display_page.add_group(
            title="Topics Options", description="Control how topics are displayed and organized"
        )

        self.group_topics_by_namespace_row = topic_options_group.add_row(
            Adw.SwitchRow(
                title="Group Topics by Namespace",
                subtitle="Organize topics by their namespace",
                active=True,
            )
        )
        self.app.settings.bind(
            "group-topics-by-namespace", self.group_topics_by_namespace_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        self.show_hidden_topics_row = topic_options_group.add_row(
            Adw.SwitchRow(
                title="Show Hidden Topics",
                subtitle="Display topics with names starting with underscore",
                active=False,
            )
        )
        self.app.settings.bind(
            "show-hidden-topics", self.show_hidden_topics_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        self.show_action_topics_row = topic_options_group.add_row(
            Adw.SwitchRow(
                title="Show Action-Related Topics",
                subtitle="Display topics created by ROS2 actions (_action/feedback, _action/status)",
                active=False,
            )
        )
        self.app.settings.bind(
            "show-action-topics", self.show_action_topics_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        self.show_parameter_events_row = topic_options_group.add_row(
            Adw.SwitchRow(
                title="Show Parameter Events Topics",
                subtitle="Display /parameter_events topics and parameter related topics",
                active=False,
            )
        )
        self.app.settings.bind(
            "show-parameter-topics", self.show_parameter_events_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        self.show_tf_topics_row = topic_options_group.add_row(
            Adw.SwitchRow(
                title="Show TF Topics",
                subtitle="Display /tf and /tf_static topics",
                active=True,
            )
        )
        self.app.settings.bind("show-tf-topics", self.show_tf_topics_row, "active", Gio.SettingsBindFlags.DEFAULT)

        # Service Options
        service_options_group = self.display_page.add_group(
            title="Service Options", description="Control how services are displayed and organized"
        )

        self.group_services_by_namespace_row = service_options_group.add_row(
            Adw.SwitchRow(
                title="Group Services by Namespace",
                subtitle="Organize services by their namespace",
                active=True,
            )
        )
        self.app.settings.bind(
            "group-services-by-namespace", self.group_services_by_namespace_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        self.show_hidden_services_row = service_options_group.add_row(
            Adw.SwitchRow(
                title="Show Hidden Services",
                subtitle="Display services with names starting with underscore",
                active=False,
            )
        )
        self.app.settings.bind(
            "show-hidden-services", self.show_hidden_services_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        self.show_parameter_services_row = service_options_group.add_row(
            Adw.SwitchRow(
                title="Show Parameter Services",
                subtitle="Display parameter-related services (.../get_parameters, .../set_parameters, etc.)",
                active=False,
            )
        )
        self.app.settings.bind(
            "show-parameter-services", self.show_parameter_services_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        self.show_action_services_row = service_options_group.add_row(
            Adw.SwitchRow(
                title="Show Action-Related Services",
                subtitle="Display services created by ROS2 actions (_action/send_goal, etc.)",
                active=False,
            )
        )
        self.app.settings.bind(
            "show-action-services", self.show_action_services_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        # Action Options
        action_options_group = self.display_page.add_group(
            title="Action Options", description="Control how actions are displayed and organized"
        )

        self.group_actions_by_namespace_row = action_options_group.add_row(
            Adw.SwitchRow(
                title="Group Actions by Namespace",
                subtitle="Organize actions by their namespace",
                active=True,
            )
        )
        self.app.settings.bind(
            "group-actions-by-namespace", self.group_actions_by_namespace_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        self.show_hidden_actions_row = action_options_group.add_row(
            Adw.SwitchRow(
                title="Show Hidden Actions",
                subtitle="Display actions with names starting with underscore",
                active=False,
            )
        )
        self.app.settings.bind(
            "show-hidden-actions", self.show_hidden_actions_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        # Parameter Options
        parameter_options_group = self.display_page.add_group(
            title="Parameter Options", description="Control how parameters are displayed and organized"
        )

        # self.group_parameters_by_namespace_row = parameter_options_group.add_row(
        #     Adw.SwitchRow(
        #         title="Group Parameters by Namespace",
        #         subtitle="Organize parameters by their namespace",
        #         active=True,
        #     )
        # )
        # self.app.settings.bind(
        #     "group-parameters-by-namespace",
        #     self.group_parameters_by_namespace_row,
        #     "active",
        #     Gio.SettingsBindFlags.DEFAULT,
        # )

        # self.show_hidden_parameters_row = parameter_options_group.add_row(
        #     Adw.SwitchRow(
        #         title="Show Hidden Parameters",
        #         subtitle="Display parameters with names starting with underscore",
        #         active=False,
        #     )
        # )
        # self.app.settings.bind(
        #     "show-hidden-parameters", self.show_hidden_parameters_row, "active", Gio.SettingsBindFlags.DEFAULT
        # )

        self.show_qos_parameters_row = parameter_options_group.add_row(
            Adw.SwitchRow(
                title="Show QoS-Related Parameters",
                subtitle="Display parameters related to Quality of Service settings",
                active=False,
            )
        )
        self.app.settings.bind(
            "show-qos-parameters", self.show_qos_parameters_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        # # Refresh and Update Settings
        # refresh_group = self.display_page.add_group(title="Refresh Behavior")

        # self.auto_refresh_row = refresh_group.add_row(
        #     Adw.SwitchRow(title="Auto Refresh", subtitle="Automatically refresh lists periodically", active=False)
        # )

        # self.refresh_interval_row = refresh_group.add_row(Adw.SpinRow.new_with_range(1, 60, 1))
        # self.refresh_interval_row.set_title("Refresh Interval (seconds)")
        # self.refresh_interval_row.set_value(5)

        # self.show_message_timestamps_row = message_group.add_row(
        #     Adw.SwitchRow(title="Show Timestamps", subtitle="Display timestamps for received messages", active=True)
        # )

        # self.max_message_history_row = message_group.add_row(Adw.SpinRow.new_with_range(10, 1000, 10))
        # self.max_message_history_row.set_title("Message History Limit")
        # self.max_message_history_row.set_subtitle("Maximum number of messages to keep in history")
        # self.max_message_history_row.set_value(100)

        # Create application behavior settings page
        # self.behavior_page = PrefPage(title="Behavior", icon_name="preferences-system-symbolic")
        # super().add(self.behavior_page)

        # Startup Behavior
        # startup_group = self.behavior_page.add_group(
        #     title="Startup Behavior", description="Configure what happens when the application starts"
        # )

        # self.restore_last_page_row = startup_group.add_row(
        #     Adw.SwitchRow(title="Restore Last Page", subtitle="Open the last viewed page on startup", active=False)
        # )

        # Navigation Behavior
        # navigation_group = self.behavior_page.add_group(
        #     title="Navigation", description="Configure navigation and window behavior"
        # )

        # self.confirm_page_close_row = navigation_group.add_row(
        #     Adw.SwitchRow(
        #         title="Confirm Page Close",
        #         subtitle="Ask for confirmation before closing pages with unsaved changes",
        #         active=True,
        #     )
        # )

        # self.remember_window_size_row = navigation_group.add_row(
        #     Adw.SwitchRow(
        #         title="Remember Window Size", subtitle="Restore window size and position on startup", active=True
        #     )
        # )

        # Performance Settings
        # performance_group = self.behavior_page.add_group(
        #     title="Performance", description="Configure performance-related settings"
        # )

        # self.max_concurrent_calls_row = performance_group.add_row(Adw.SpinRow.new_with_range(1, 20, 1))
        # self.max_concurrent_calls_row.set_title("Max Concurrent Service Calls")
        # self.max_concurrent_calls_row.set_value(5)

        # self.enable_debug_logging_row = performance_group.add_row(
        #     Adw.SwitchRow(
        #         title="Enable Debug Logging", subtitle="Enable detailed logging for troubleshooting", active=False
        #     )
        # )

        # # Reset Settings
        # reset_group = self.behavior_page.add_group(title="Reset")

        # self.reset_settings_row = reset_group.add_row(
        #     ButtonRow(
        #         label="Reset All Settings",
        #         tooltip_text="Reset all preferences to default values",
        #         func=self.on_reset_settings,
        #     )
        # )

    def update_env_vars(self, *args):
        """Update environment variable entries from current environment"""
        env_auto_discovery = os.getenv("ROS_AUTOMATIC_DISCOVERY_RANGE", default="")
        self.env_auto_discovery_row.set_text(env_auto_discovery)

        env_static_peers = os.getenv("ROS_STATIC_PEERS", default="")
        self.env_static_peers_row.set_text(env_static_peers)

        env_domain_id = os.getenv("ROS_DOMAIN_ID", default="")
        self.env_domain_id_row.set_text(env_domain_id)

        env_discovery_server = os.getenv("ROS_DISCOVERY_SERVER", default="")
        self.env_discovery_server_row.set_text(env_discovery_server)

    def on_apply_env_var(self, entry_row: Adw.EntryRow, env_var_name: str, *args):
        """Apply environment variables and restart ROS2 node"""
        self.ros2_connector.stop_node()
        os.environ[env_var_name] = entry_row.get_text().strip()

        # os.environ["ROS_AUTOMATIC_DISCOVERY_RANGE"] = self.env_auto_discovery_row.get_text()
        # os.environ["ROS_STATIC_PEERS"] = self.env_static_peers_row.get_text()
        # os.environ["ROS_DOMAIN_ID"] = self.env_domain_id_row.get_text()
        # os.environ["ROS_DISCOVERY_SERVER"] = self.env_discovery_server_row.get_text()

        # self.add_toast(Adw.Toast(title="Applied Environment Variables"))
        self.ros2_connector.start_node()

    def on_apply_gui_node_name(self, *args):
        """Handle built-in apply button for node name"""
        node_name = self.gui_node_name_row.get_text().strip()

        if not node_name:
            self.add_toast(Adw.Toast(title="Node name cannot be empty"))
            return

        try:
            validate_node_name(node_name)
            self.ros2_connector.stop_node()
            self.ros2_connector.start_node(node_name=node_name)
            self.app.settings.set_string("gui-node-name", node_name)
            self.add_toast(Adw.Toast(title=f"Applied GUI-Node name: '{node_name}'"))

        except InvalidNodeNameException as e:
            self.add_toast(Adw.Toast(title=f"Error: {e}"))
            return

    def on_apply_gui_node_namespace(self, *args):
        """Handle built-in apply button for node namespace"""
        node_namespace = self.gui_node_namespace_row.get_text().strip()
        node_name = self.gui_node_name_row.get_text().strip()

        if not node_namespace:
            full_namespace = f"/{node_name}"
        elif not node_namespace.startswith("/"):
            full_namespace = f"/{node_namespace}/{node_name}"
        else:
            full_namespace = f"{node_namespace}/{node_name}"

        try:
            validate_namespace(full_namespace)
            self.app.settings.set_string("gui-node-namespace", node_namespace)
            self.ros2_connector.stop_node()
            self.ros2_connector.start_node(node_name=node_name, node_namespace=node_namespace)
            self.add_toast(Adw.Toast(title=f"Applied full GUI-Node name: '{full_namespace}'"))

        except InvalidNamespaceException as e:
            self.add_toast(Adw.Toast(title=f"Error: {e}"))
            return

    def on_toggle_ros2_node(self, btn: PlayPauseButton, active: bool, *args):
        """Toggle ROS2 node on/off"""
        if active:
            self.get_root().app.activate_action("ros2-node-start", None)
            self.add_toast(Adw.Toast(title="Started ROS2 Node"))
        else:
            self.get_root().app.activate_action("ros2-node-stop", None)
            self.add_toast(Adw.Toast(title="Stopped ROS2 Node"))

    def on_change_node_running_state(self, action: Gio.Action, state):
        """Update UI when ROS2 node state changes"""
        is_running = action.get_state().get_boolean()
        self.controls_row.set_subtitle(f"ROS2 Node is {'running' if is_running else 'not running'}")

    # def on_reset_settings(self, *args):
    #     """Reset all settings to default values"""
    #     dialog = Adw.MessageDialog.new(
    #         self.get_root(),
    #         "Reset All Settings?",
    #         "This will reset all preferences to their default values. This action cannot be undone.",
    #     )
    #     dialog.add_response("cancel", "Cancel")
    #     dialog.add_response("reset", "Reset")
    #     dialog.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)
    #     dialog.set_default_response("cancel")
    #     dialog.set_close_response("cancel")

    #     def on_response(dialog, response):
    #         if response == "reset":
    #             try:
    #                 # Reset settings through the application
    #                 for key in self.app.settings.list_keys():
    #                     self.app.settings.reset(key)

    #                 self.add_toast(Adw.Toast(title="Settings reset to defaults"))

    #             except Exception as e:
    #                 self.add_toast(Adw.Toast(title=f"Error resetting settings: {e}"))

    #     dialog.connect("response", on_response)
    #     dialog.present()

    def on_close_attempt(self, *args):
        """Handle dialog close"""
        if hasattr(self, "node_state_changed_handler"):
            self.disconnect(self.node_state_changed_handler)
