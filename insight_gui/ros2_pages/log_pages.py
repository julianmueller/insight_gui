from enum import Enum

from rcl_interfaces.msg import Log

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import TextViewRow, MultiToggleButtonRow
from insight_gui.widgets.buttons import PlayPauseButton


class LogLevel(Enum):
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    FATAL = 50

    @classmethod
    def from_value(cls, value: int):
        for level in cls:
            if level.value == value:
                return level
        raise ValueError(f"No LogLevel found for value: {value}")

    def __str__(self):
        return self.name


class LoggerPage(Adw.NavigationPage):
    __gtype_name__ = "LoggerPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Logger")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(refresh_enabled=False, search_enabled=True)
        self.content_page.set_search_entry_placeholder_text("Search for log entries")
        super().set_child(self.content_page)

        self.is_logging = False

        # Btn for opening the online link to msg definition
        self.play_pause_btn = self.content_page.add_header_widget(
            PlayPauseButton(
                default_play=False,
                func=self.toggle_logging,
                play_tooltip="Start logging",
                pause_tooltip="Stop logging",
            )
        )

        # top bar with toggle btns that filter certain logLevels (debug, info, warning, error, etc)
        filters_group: PrefGroup = self.content_page.pref_page.add_group(vexpand=True)
        # filters_group.listbox.set_vexpand(True)
        self.filters_row = filters_group.add_row(
            MultiToggleButtonRow(title="Filter Severity Levels", subtitle="toggle to show/hide the respective logs")
        )

        self.debug_filter_btn = self.filters_row.add_toggle_btn(
            unique_id=str(LogLevel.DEBUG), labels="DEBUG", default_active=True, css_classes=[]
        )
        self.info_filter_btn = self.filters_row.add_toggle_btn(
            unique_id=str(LogLevel.INFO), labels="INFO", default_active=True, css_classes=["success"]
        )
        self.warning_filter_btn = self.filters_row.add_toggle_btn(
            unique_id=str(LogLevel.WARN), labels="WARN", default_active=True, css_classes=["warning"]
        )
        self.error_filter_btn = self.filters_row.add_toggle_btn(
            unique_id=str(LogLevel.ERROR), labels="ERROR", default_active=True, css_classes=["error"]
        )
        self.fatal_filter_btn = self.filters_row.add_toggle_btn(
            unique_id=str(LogLevel.FATAL), labels="FATAL", default_active=True, css_classes=["error"]
        )

        # TODO make this extend to the bottom of the screen (somehow vexpand does not work)
        # TODO change this into something like rqt has, a scrollable list with selectable entries, that can be inspected
        self.text_view_row: TextViewRow = filters_group.add_row(
            TextViewRow(
                title="Log of '/rosout'",
                subtitle="press start to see incoming logs",
                show_copy_btn=True,
                editable=False,
                vexpand=True,
                min_height=500,
                max_height=800,
            )
        )
        self.text_view_row.add_tag(LogLevel.DEBUG, background="lightblue")
        self.text_view_row.add_tag(LogLevel.INFO, background="lightgreen")
        self.text_view_row.add_tag(LogLevel.WARN, background="orange")
        self.text_view_row.add_tag(LogLevel.ERROR, background="red")
        self.text_view_row.add_tag(LogLevel.FATAL, background="purple")

        # TODO this is only for debugging
        self.text_view_row.append_tagged_text("[DEBUG]\n", "DEBUG")
        self.text_view_row.append_tagged_text("[INFO]\n", "INFO")
        self.text_view_row.append_tagged_text("[WARN]\n", "WARN")
        self.text_view_row.append_tagged_text("[ERROR]\n", "ERROR")
        self.text_view_row.append_tagged_text("[FATAL]\n", "FATAL")

        self.rosout_sub = self.ros2_connector.add_subsciption(Log, "/rosout", self.log_callback)
        self.filters_row.connect("buttons-changed", self.on_filters_changed)

    def on_filters_changed(self, widget, *args):
        active_filters = widget.get_active_buttons()
        # print(active_filters)
        self.text_view_row.filter_by_tags(active_filters)

    def toggle_logging(self, playing: bool, *args):
        if playing:
            self.is_logging = True
            self.content_page.show_toast("started logging")
        else:
            self.is_logging = False
            self.content_page.show_toast("stopped logging")

    def log_callback(self, msg: Log):
        if self.is_logging:
            log_message = f"[{LogLevel(msg.level)}] [{msg.stamp.sec}.{msg.stamp.nanosec}] {msg.name}: {msg.msg}"
            print(log_message)
            self.text_view_row.append_tagged_text(log_message + "\n", str(LogLevel(msg.level)))
            self.text_view_row.scroll_to_end()
