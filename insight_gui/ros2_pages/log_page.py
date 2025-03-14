# Copyright (C) 2025  Julian Müller

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from enum import Enum
from datetime import datetime

from rcl_interfaces.msg import Log
from rclpy.logging import get_logger, LoggingSeverity
from ros2node.api import get_node_names


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, Gio

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import (
    PrefRow,
    TextViewRow,
    MultiToggleButtonRow,
    ColumnViewRow,
)
from insight_gui.widgets.buttons import PlayPauseButton


class LogMessage(GObject.Object):
    """A GObject that represents a log message with timestamp, severity, and message."""

    def __init__(
        self,
        *,
        unix_time: float,
        severity: LoggingSeverity,
        message: str,
        node_name: str,
    ):
        super().__init__()

        self._timestamp = datetime.fromtimestamp(unix_time).strftime("%Y-%m-%d %H:%M:%S.%f")
        self._severity = str(severity.name)
        self._message = str(message)
        self._node_name = node_name

    @GObject.Property(type=str)
    def timestamp(self) -> str:
        return self._timestamp

    @GObject.Property(type=str)
    def severity(self) -> str:
        return self._severity

    @GObject.Property(type=str)
    def message(self) -> str:
        return self._message

    @GObject.Property(type=str)
    def node(self) -> str:
        return self._node_name


class LoggerPage(ContentPage):
    __gtype_name__ = "LoggerPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(refreshable=False, searchable=False, **kwargs)
        super().set_title("Logger")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})

        self.is_logging = False

        # Btn for opening the online link to msg definition
        self.play_pause_btn = super().add_bottom_widget(
            PlayPauseButton(
                default_active=self.is_logging,
                func=self.on_toggle_logging,
                labels=("Stop logging", "Start logging"),
            ),
            position="start",
        )
        super().add_bottom_right_btn(label="Clear Log", icon_name="trash-symbolic", func=self.on_clear_log)

        # filters to apply to the column view
        filters_group: PrefGroup = self.pref_page.add_group(title="Filters", filterable=False)
        self.severity_filter_row: MultiToggleButtonRow = filters_group.add_row(
            MultiToggleButtonRow(
                title="Severity Levels",
                subtitle="toggle to show/hide the respective logs",
            )
        )

        self.debug_filter_btn = self.severity_filter_row.add_toggle_btn(
            unique_id=str(LoggingSeverity.DEBUG.name),
            labels="DEBUG",
            default_active=True,
            css_classes=[],
        )
        self.info_filter_btn = self.severity_filter_row.add_toggle_btn(
            unique_id=str(LoggingSeverity.INFO.name),
            labels="INFO",
            default_active=True,
            css_classes=["success"],
        )
        self.warning_filter_btn = self.severity_filter_row.add_toggle_btn(
            unique_id=str(LoggingSeverity.WARN.name),
            labels="WARN",
            default_active=True,
            css_classes=["warning"],
        )
        self.error_filter_btn = self.severity_filter_row.add_toggle_btn(
            unique_id=str(LoggingSeverity.ERROR.name),
            labels="ERROR",
            default_active=True,
            css_classes=["error"],
        )
        self.fatal_filter_btn = self.severity_filter_row.add_toggle_btn(
            unique_id=str(LoggingSeverity.FATAL.name),
            labels="FATAL",
            default_active=True,
            css_classes=["error"],
        )
        self.severity_filter_row.connect("button-toggled", self.on_severities_changed)

        # Filter msgs
        self.regex_msg_filter_row = filters_group.add_row(
            Adw.EntryRow(title="Regex Message Filter", text="", show_apply_button=True)
        )
        self.regex_msg_filter_row.connect_data("apply", self.on_regex_msg_filter_change)

        # Filter nodes
        self.regex_node_filter_row = filters_group.add_row(
            Adw.EntryRow(title="Regex Node Filter", text="", show_apply_button=True)
        )
        self.regex_node_filter_row.connect_data("apply", self.on_regex_node_filter_changed)

        # self.node_filter_row = filters_group.add_row(Adw.ComboRow(title="Node Filter", enable_search=True))
        # self.node_filter_row.connect("notify::selected-item", self.on_node_filter_changed)
        # self.node_list_store = Gio.ListStore.new(Gtk.StringObject)

        log_group: PrefGroup = self.pref_page.add_group(title="Logs", filterable=False)
        # TODO add a limit of row, that old ones are deleted after a while
        # TODO vextend this to fill out the whole screen
        self.column_view_row: ColumnViewRow = log_group.add_row(ColumnViewRow(row_object=LogMessage))
        self.column_view_row.add_column("Timestamp", "timestamp", is_sortable=True, is_numeric=False)
        self.column_view_row.add_column("Severity", "severity", is_sortable=True, is_numeric=False)
        self.column_view_row.add_column("Message", "message", is_sortable=False, is_numeric=False, expand=True)
        self.column_view_row.add_column("Node", "node", is_sortable=True, is_numeric=False, expand=False)

        self.rosout_sub = self.ros2_connector.add_subsciption(Log, "/rosout", self.log_callback)

        # # Get the default ROS logger and attach a custom log handler
        # logger = get_logger("custom_logger")
        # logger.set_handler(custom_log_handler)

    # @property
    # def is_logging(self) -> bool:
    #     return self.play_pause_btn.is_active

    def on_severities_changed(self, widget: MultiToggleButtonRow, *args):
        active_log_levels = widget.get_active_buttons()
        self.column_view_row.apply_filter(severity=list(active_log_levels.keys()))

    def on_regex_msg_filter_change(self, *args):
        text = self.regex_msg_filter_row.get_text()
        self.column_view_row.apply_filter(message=text)

    def on_regex_node_filter_changed(self, *args):
        text = self.regex_node_filter_row.get_text()
        self.column_view_row.apply_filter(node=text)

    def on_node_filter_changed(self, *args):
        node_name = self.node_filter_row.get_selected_item().get_string()
        self.column_view_row.apply_filter(node_name=node_name)

    # TODO do i need this?
    # def on_refresh_node_list(self, *args):
    #     self.node_list_store.remove_all()
    #     available_nodes = get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True)
    #     for node_name, node_namespace, node_full_name in sorted(available_nodes):
    #         self.node_list_store.append(Gtk.StringObject.new(node_full_name))
    #     self.node_filter_row.set_model(self.node_list_store)

    def on_toggle_logging(self, btn: Gtk.Widget, playing: bool, *args):
        self.is_logging = playing

    def log_callback(self, msg: Log):
        if self.is_logging:
            self.column_view_row.add_row(
                LogMessage(
                    unix_time=float(msg.stamp.sec + msg.stamp.nanosec / 1e9),
                    severity=LoggingSeverity(msg.level),
                    message=msg.msg,
                    node_name=msg.name,
                )
            )

    def on_clear_log(self, *args):
        self.column_view_row.clear_rows()

    def on_save_log(self, *args):
        # TODO
        pass
