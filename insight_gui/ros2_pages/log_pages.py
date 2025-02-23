from enum import Enum

from rcl_interfaces.msg import Log

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import TextViewRow
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
                callback=self.toggle_logging,
                play_tooltip="Start logging",
                pause_tooltip="Stop logging",
            )
        )

        # top bar with toggle btns that filter certain logLevels (debug, info, warning, error, etc)
        filters_group = self.content_page.pref_page.add_group()
        self.filters_row = filters_group.add_row(FiltersRow())
        self.filters_row.connect("filters-changed", self.filters_changed)

        # text_group = self.content_page.pref_page.add_group(title="Logging")
        self.text_view_row: TextViewRow = filters_group.add_row(
            TextViewRow(
                title="Log of '/rosout'",
                subtitle="press start to see incoming logs",
                show_copy_btn=True,
                editable=False,
            )
        )
        self.text_view_row.add_tag(LogLevel.DEBUG, background="lightblue")
        self.text_view_row.add_tag(LogLevel.INFO, background="lightgreen")
        self.text_view_row.add_tag(LogLevel.WARN, background="orange")
        self.text_view_row.add_tag(LogLevel.ERROR, background="red")
        self.text_view_row.add_tag(LogLevel.FATAL, background="purple")

        self.text_view_row.append_tagged_text("[DEBUG]\n", "DEBUG")
        self.text_view_row.append_tagged_text("[INFO]\n", "INFO")
        self.text_view_row.append_tagged_text("[WARN]\n", "WARN")
        self.text_view_row.append_tagged_text("[ERROR]\n", "ERROR")
        self.text_view_row.append_tagged_text("[FATAL]\n", "FATAL")

        self.rosout_sub = self.ros2_connector.add_subsciption(Log, "/rosout", self.log_callback)

    def toggle_logging(self, *args):
        if self.is_logging:
            self.is_logging = False
            self.content_page.show_toast("stopped logging")
        else:
            self.is_logging = True
            self.content_page.show_toast("started logging")

    def log_callback(self, msg: Log):
        if self.is_logging:
            log_message = f"[{LogLevel(msg.level)}] [{msg.stamp.sec}.{msg.stamp.nanosec}] {msg.name}: {msg.msg}"
            print(log_message)
            self.text_view_row.append_tagged_text(log_message + "\n", str(LogLevel(msg.level)))
            self.text_view_row.scroll_to_end()

    def filters_changed(self, widget, *args):
        active_filters = widget.get_active_filters()
        print(active_filters)
        self.text_view_row.filter_by_tags(active_filters)


class FiltersRow(Adw.PreferencesRow):
    __gtype_name__ = "FiltersRow"
    __gsignals__ = {"filters-changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_activatable(False)

        filters_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
            homogeneous=True,
        )
        super().set_child(filters_box)

        self.debug_filter_btn = Gtk.ToggleButton(label="DEBUG", active=True, css_classes=[])
        self.debug_filter_btn.connect("toggled", self.on_filter_toggled)
        filters_box.append(self.debug_filter_btn)

        self.info_filter_btn = Gtk.ToggleButton(label="INFO", active=True, css_classes=[])
        self.info_filter_btn.connect("toggled", self.on_filter_toggled)
        filters_box.append(self.info_filter_btn)

        self.warning_filter_btn = Gtk.ToggleButton(label="WARN", active=True, css_classes=["warning"])
        self.warning_filter_btn.connect("toggled", self.on_filter_toggled)
        filters_box.append(self.warning_filter_btn)

        self.error_filter_btn = Gtk.ToggleButton(label="ERROR", active=True, css_classes=["error"])
        self.error_filter_btn.connect("toggled", self.on_filter_toggled)
        filters_box.append(self.error_filter_btn)

        self.fatal_filter_btn = Gtk.ToggleButton(label="FATAL", active=True, css_classes=["error"])
        self.fatal_filter_btn.connect("toggled", self.on_filter_toggled)
        filters_box.append(self.fatal_filter_btn)

    def get_active_filters(self) -> list:
        active_filters = []
        if self.debug_filter_btn.get_active():
            active_filters.append("DEBUG")
        if self.info_filter_btn.get_active():
            active_filters.append("INFO")
        if self.warning_filter_btn.get_active():
            active_filters.append("WARN")
        if self.error_filter_btn.get_active():
            active_filters.append("ERROR")
        if self.fatal_filter_btn.get_active():
            active_filters.append("FATAL")
        return active_filters

    def on_filter_toggled(self, button):
        super().emit("filters-changed")
