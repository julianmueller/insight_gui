# =============================================================================
# window.py
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

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio, GLib

from insight_gui.ros2_pages.pkg_list_page import PackageListPage
from insight_gui.ros2_pages.node_list_page import NodeListPage
from insight_gui.ros2_pages.interface_browser_page import InterfaceBrowserPage
from insight_gui.ros2_pages.topic_list_page import TopicListPage
from insight_gui.ros2_pages.topic_echo_page import TopicEchoPage
from insight_gui.ros2_pages.service_list_page import ServiceListPage
from insight_gui.ros2_pages.service_call_page import ServiceCallPage
from insight_gui.ros2_pages.action_list_page import ActionListPage
from insight_gui.ros2_pages.graph_page import GraphPage
from insight_gui.ros2_pages.param_page import ParameterListPage
from insight_gui.ros2_pages.tf_page import TransformsPage
from insight_gui.ros2_pages.log_page import LoggerPage
from insight_gui.ros2_pages.doctor_page import DoctorPage
from insight_gui.ros2_pages.img_viewer_page import ImageViewerPage
from insight_gui.ros2_pages.joint_states_page import JointStatesPage
from insight_gui.ros2_pages.preferences_dialog import PreferencesDialog

from insight_gui.utils.adw_colors import AdwAccentColor


@Gtk.Template(filename=str(Path(__file__).with_suffix(".ui")))
class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    split_view: Adw.NavigationSplitView = Gtk.Template.Child()

    nav_header_bar: Adw.HeaderBar = Gtk.Template.Child()
    refresh_btn: Gtk.Button = Gtk.Template.Child()
    menu_btn: Gtk.Button = Gtk.Template.Child()

    # content_header_bar: Adw.HeaderBar = Gtk.Template.Child()
    content_stack: Gtk.Stack = Gtk.Template.Child()

    # all nav views for the pages
    pkg_list_nav_view: Adw.NavigationView = Gtk.Template.Child()
    node_list_nav_view: Adw.NavigationView = Gtk.Template.Child()
    topic_list_nav_view: Adw.NavigationView = Gtk.Template.Child()
    topic_echo_nav_view: Adw.NavigationView = Gtk.Template.Child()
    service_list_nav_view: Adw.NavigationView = Gtk.Template.Child()
    srv_caller_nav_view: Adw.NavigationView = Gtk.Template.Child()
    action_list_nav_view: Adw.NavigationView = Gtk.Template.Child()
    interface_browser_nav_view: Adw.NavigationView = Gtk.Template.Child()
    scrolled_graph_parent: Gtk.ScrolledWindow = Gtk.Template.Child()
    param_list_nav_view: Adw.NavigationView = Gtk.Template.Child()
    tf_nav_view: Adw.NavigationView = Gtk.Template.Child()
    img_viewer_nav_view: Adw.NavigationView = Gtk.Template.Child()
    joint_states_nav_view: Adw.NavigationView = Gtk.Template.Child()
    logger_nav_view: Adw.NavigationView = Gtk.Template.Child()
    doctor_nav_view: Adw.NavigationView = Gtk.Template.Child()

    # ros time
    time_box: Gtk.Box = Gtk.Template.Child()
    ros_time_lbl: Gtk.Label = Gtk.Template.Child()
    ros_elapsed_time_lbl: Gtk.Label = Gtk.Template.Child()
    wall_time_lbl: Gtk.Label = Gtk.Template.Child()
    wall_elapsed_time_lbl: Gtk.Label = Gtk.Template.Child()
    # TODO also add the boxes?

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_accent_colors()

        self.ros2_connector.start_node()

        self.refresh_btn.set_visible(False)  # TODO do i still need this?

        # content of the stack
        self.pkg_list_nav_view.add(PackageListPage())
        self.node_list_nav_view.add(NodeListPage())
        self.topic_list_nav_view.add(TopicListPage())
        self.topic_echo_nav_view.add(TopicEchoPage())
        self.service_list_nav_view.add(ServiceListPage())
        self.srv_caller_nav_view.add(ServiceCallPage())
        self.action_list_nav_view.add(ActionListPage())
        self.interface_browser_nav_view.add(InterfaceBrowserPage())
        self.scrolled_graph_parent.set_child(GraphPage(self.ros2_connector))
        self.param_list_nav_view.add(ParameterListPage())
        self.tf_nav_view.add(TransformsPage())
        self.img_viewer_nav_view.add(ImageViewerPage())
        self.joint_states_nav_view.add(JointStatesPage())
        self.logger_nav_view.add(LoggerPage())
        self.doctor_nav_view.add(DoctorPage())

        # Preferences
        self.preferences_dialog = PreferencesDialog(ros2_connector=self.ros2_connector)
        self.about_dialog = Adw.AboutDialog(
            application_name="Insight",
            application_icon="insight-logo",
            developer_name="Julian Müller",
            # developer_documentation="https://github.com/julianmueller/insight_gui",
            license_type=Gtk.License.APACHE_2_0,
            version="0.0.1",
            website="https://github.com/julianmueller/insight_gui",
        )
        self.about_dialog.add_credit_section("Development", ["Julian Müller"])
        self.about_dialog.add_credit_section("Inspiration", ["rqt", "ros2cli"])

        # Actions
        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", lambda *_: self.preferences_dialog.present(self))
        self.app.add_action(action)

        # TODO add shortcuts dialog
        # action = Gio.SimpleAction.new("shortcuts", None)
        # action.connect("activate", lambda *_: self.shortcuts_dialog.present(self))
        # self.app.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", lambda *_: self.about_dialog.present(self))
        self.app.add_action(action)

        # action = Gio.SimpleAction.new("quit", None)
        # action.connect("activate", self.on_quit)
        # self.app.add_action(action)

        # Shortcuts # TODO make them also work in the detached windows
        self.shortcut_controller = Gtk.ShortcutController()
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Control>f"),
                action=Gtk.CallbackAction.new(self.on_search_shortcut),
            )
        )
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Control>r"),
                action=Gtk.CallbackAction.new(self.on_refresh_shortcut),
            )
        )
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("F5"),
                action=Gtk.CallbackAction.new(self.on_refresh_shortcut),
            )
        )
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Control><Shift>n"),
                action=Gtk.CallbackAction.new(self.on_detach_shortcut),
            )
        )
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.ShortcutTrigger.parse_string("<Control>w"),
                action=Gtk.CallbackAction.new(lambda *_: self.close()),
            )
        )

        # Add controller to window
        self.add_controller(self.shortcut_controller)

        # update time labels
        GLib.idle_add(self.update_time_labels)

    @property
    def ros2_connector(self):
        return self.app.ros2_connector

    @property
    def app(self):
        return self.get_application()

    # @Gtk.Template.Callback()
    # def on_menu_btn_clicked(self, *args):
    #     self.preferences_dialog.present(self)

    # @Gtk.Template.Callback()
    # def on_refresh_btn_clicked(self, *args):
    #     for stack_page in self.content_stack.get_pages():
    #         nav_view = stack_page.get_child()
    #         nav_page = nav_view.get_navigation_stack()[0]
    #         refresh_func = getattr(nav_page, "refresh", None)
    #         if callable(refresh_func):
    #             refresh_func()

    def on_search_shortcut(self, *args):
        self.content_stack.get_visible_child().get_visible_page().show_search_bar()

    def on_refresh_shortcut(self, *args):
        self.content_stack.get_visible_child().get_visible_page().on_refresh()

    def on_detach_shortcut(self, *args):
        self.content_stack.get_visible_child().get_visible_page().on_detach()

    def update_time_labels(self):
        node_is_running = self.app.lookup_action("ros2_node_is_running").get_state().get_boolean()

        if not node_is_running:
            self.time_box.set_visible(False)
        else:
            self.time_box.set_visible(True)
            current_time = 0
            try:
                current_time = self.ros2_connector.node.get_clock().now()
            except AttributeError as e:
                return True
            elapsed = current_time - self.ros2_connector.start_time

            self.ros_time_lbl.set_text(f"{(current_time.nanoseconds / 1e9):.2f} s")
            self.ros_elapsed_time_lbl.set_text(f"{(elapsed.nanoseconds / 1e9):.2f} s")

            # TODO if use_sim_time is true, show the simulation time
            # self.wall_time_lbl.set_text(f"{(current_time.nanoseconds / 1e9):.2f} s")
            # self.wall_elapsed_time_lbl.set_text(f"{(elapsed.nanoseconds / 1e9):.2f} s")

        return True  # keep GLib thread running

    # add accent colors
    def _setup_accent_colors(self):
        css_string = ""

        # assemble the css file as a string
        for adw_col in list(AdwAccentColor):
            css_string += adw_col.as_css_style() + "\n"

        css_string += """
        .small-button {
            min-width: 24px;
            min-height: 24px;
        }
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css_string)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def get_dark(self):
        style_manager = Adw.StyleManager.get_default()
        return style_manager.get_dark()
