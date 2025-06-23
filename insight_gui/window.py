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
from typing import Type

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio, GLib, GObject

from insight_gui.ros2_pages.welcome_page import WelcomePage
from insight_gui.ros2_pages.pkg_list_page import PackageListPage
from insight_gui.ros2_pages.node_list_page import NodeListPage
from insight_gui.ros2_pages.topic_list_page import TopicListPage
from insight_gui.ros2_pages.topic_pub_page import TopicPublisherPage
from insight_gui.ros2_pages.topic_sub_page import TopicSubscriberPage
from insight_gui.ros2_pages.service_list_page import ServiceListPage
from insight_gui.ros2_pages.service_call_page import ServiceCallPage
from insight_gui.ros2_pages.action_goal_page import ActionGoalPage
from insight_gui.ros2_pages.action_list_page import ActionListPage
from insight_gui.ros2_pages.launch_list_page import LaunchListPage
from insight_gui.ros2_pages.interface_browser_page import InterfaceBrowserPage
from insight_gui.ros2_pages.graph_page import GraphPage
from insight_gui.ros2_pages.param_list_page import ParameterListPage
from insight_gui.ros2_pages.tf_page import TransformsPage
from insight_gui.ros2_pages.img_viewer_page import ImageViewerPage
from insight_gui.ros2_pages.joint_states_page import JointStatesPage
from insight_gui.ros2_pages.teleop_page import TeleoperatorPage
from insight_gui.ros2_pages.log_page import LoggerPage
from insight_gui.ros2_pages.doctor_page import DoctorPage

from insight_gui.ros2_pages.preferences_dialog import PreferencesDialog

from insight_gui.utils.adw_colors import AdwAccentColor
from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.stack_sidebar import StackSidebar


class BaseWindow(Adw.ApplicationWindow):
    __gtype_name__ = "BaseWindow"

    def __init__(self, app: Adw.Application, **kwargs):
        super().__init__(application=app, **kwargs)
        self.app: Adw.Application = app
        self.ros2_connector: ROS2Connector = app.ros2_connector

        self._setup_accent_colors()

        # window actions
        action = Gio.SimpleAction.new("close", None)
        action.connect("activate", self.on_close)
        self.add_action(action)

        action = Gio.SimpleAction.new("refresh", None)
        action.connect("activate", self.on_refresh)
        self.add_action(action)

        action = Gio.SimpleAction.new("toggle-search", None)
        action.connect("activate", self.on_toggle_search)
        self.add_action(action)

        action = Gio.SimpleAction.new("detach", None)
        action.connect("activate", self.on_detach)
        self.add_action(action)

        action = Gio.SimpleAction.new("page-trigger", None)
        action.connect("activate", self.on_page_trigger)
        self.add_action(action)

        # Shortcuts
        self.shortcut_controller = Gtk.ShortcutController()
        self.shortcut_controller.set_scope(Gtk.ShortcutScope.LOCAL)
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.AlternativeTrigger.new(
                    Gtk.KeyvalTrigger.new(Gdk.KEY_r, Gdk.ModifierType.CONTROL_MASK),
                    Gtk.KeyvalTrigger.new(Gdk.KEY_F5, Gdk.ModifierType.NO_MODIFIER_MASK),
                ),
                action=Gtk.NamedAction.new("win.refresh"),
            )
        )
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.KeyvalTrigger.new(Gdk.KEY_f, Gdk.ModifierType.CONTROL_MASK),
                action=Gtk.NamedAction.new("win.toggle-search"),
            )
        )
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.KeyvalTrigger.new(Gdk.KEY_d, Gdk.ModifierType.CONTROL_MASK),
                action=Gtk.NamedAction.new("win.detach"),
            )
        )

        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.KeyvalTrigger.new(Gdk.KEY_Return, Gdk.ModifierType.CONTROL_MASK),
                action=Gtk.NamedAction.new("win.page-trigger"),
            )
        )
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.KeyvalTrigger.new(Gdk.KEY_w, Gdk.ModifierType.CONTROL_MASK),
                action=Gtk.NamedAction.new("win.close"),
            )
        )

        # Add controller to window
        self.add_controller(self.shortcut_controller)

    def on_refresh(self, *args):
        if self.current_page and self.current_page.refreshable:
            self.current_page.refresh()

    def on_detach(self, *args):
        if self.current_page and self.current_page.detachable:
            self.current_page.detach()

    def on_toggle_search(self, *args):
        if self.current_page and self.current_page.searchable:
            self.current_page.toggle_search()

    def on_page_trigger(self, *args):
        if self.current_page:
            self.current_page.trigger()

    def on_close(self, *args):
        self.close()

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
        return Adw.StyleManager.get_default().get_dark()


class MainWindow(BaseWindow):
    __gtype_name__ = "MainWindow"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_default_size(1200, 800)
        super().set_size_request(400, 500)

        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(Path(__file__).with_suffix(".ui")))

        self.split_view: Adw.NavigationSplitView = builder.get_object("split_view")
        super().set_content(self.split_view)

        break_point = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 800sp"))
        break_point.add_setter(self.split_view, "collapsed", True)
        super().add_breakpoint(break_point)

        self.nav_header_bar: Adw.HeaderBar = builder.get_object("nav_header_bar")
        self.menu_btn: Gtk.Button = builder.get_object("menu_btn")
        self.content_stack: Gtk.Stack = builder.get_object("content_stack")
        self.content_stack.connect("notify::visible-child-name", self.on_stack_page_changed)

        self.stack_sidebar: StackSidebar = builder.get_object("stack_sidebar")
        self.stack_sidebar.set_stack(self.content_stack)

        welcome_view = Adw.NavigationView()
        welcome_view.add(WelcomePage())
        self.content_stack.add_named(welcome_view, "welcome")
        self.content_stack.set_visible_child_name("welcome")

        # Package Management
        pkg_group = self.stack_sidebar.add_group(title="Packages")
        self.stack_sidebar.add_page_row(
            group=pkg_group,
            title="Packages",
            page_name="pkg_list",
            nav_page=PackageListPage(),
            prefix_icon="packages-app-symbolic",
            subtitle="Browse all packages",
        )

        # Nodes
        node_group = self.stack_sidebar.add_group(title="Nodes")
        self.stack_sidebar.add_page_row(
            group=node_group,
            title="Node List",
            page_name="node_list",
            nav_page=NodeListPage(),
            prefix_icon="center-symbolic",
            subtitle="Browse all active nodes",
        )
        self.stack_sidebar.add_page_row(
            group=node_group,
            title="Launch Files",
            page_name="launch_list",
            nav_page=LaunchListPage(),
            # prefix_icon="rocket-symbolic",
            prefix_icon="media-playback-start-symbolic",
            subtitle="Browse launch files",
        )
        self.stack_sidebar.add_page_row(
            group=node_group,
            title="Parameters",
            page_name="param_list",
            nav_page=ParameterListPage(),
            prefix_icon="function-third-order-symbolic",
            subtitle="Manage node parameters",
        )
        self.stack_sidebar.add_page_row(
            group=node_group,
            title="Graph",
            page_name="graph_page",
            nav_page=GraphPage(),
            prefix_icon="network-proxy-symbolic",
            subtitle="ROS2 computational graph",
        )

        # Topics
        topic_group = self.stack_sidebar.add_group(title="Topics")
        self.stack_sidebar.add_page_row(
            group=topic_group,
            title="Topic List",
            page_name="topic_list",
            nav_page=TopicListPage(),
            prefix_icon="list-compact-symbolic",
            subtitle="Browse topics",
        )
        self.stack_sidebar.add_page_row(
            group=topic_group,
            title="Publisher",
            page_name="topic_pub",
            nav_page=TopicPublisherPage(),
            prefix_icon="megaphone-symbolic",
            subtitle="Publish to topics",
        )
        self.stack_sidebar.add_page_row(
            group=topic_group,
            title="Subscriber",
            page_name="topic_sub",
            nav_page=TopicSubscriberPage(),
            prefix_icon="listen-symbolic",
            subtitle="Subscribe to topics",
        )
        self.stack_sidebar.add_page_row(
            group=topic_group,
            title="Image Viewer",
            page_name="img_viewer",
            nav_page=ImageViewerPage(),
            prefix_icon="image-x-generic-symbolic",
            subtitle="View image topics",
        )
        self.stack_sidebar.add_page_row(
            group=topic_group,
            title="Transforms",
            page_name="tf",
            nav_page=TransformsPage(),
            prefix_icon="vertical-arrows-symbolic",
            subtitle="Inspect transformations",
        )

        # Services
        service_group = self.stack_sidebar.add_group(title="Services")
        self.stack_sidebar.add_page_row(
            group=service_group,
            title="Service List",
            page_name="service_list",
            nav_page=ServiceListPage(),
            prefix_icon="list-compact-symbolic",
            subtitle="Browse services",
        )
        self.stack_sidebar.add_page_row(
            group=service_group,
            title="Service Caller",
            page_name="srv_caller",
            nav_page=ServiceCallPage(),
            prefix_icon="call-start-symbolic",
            subtitle="Call services",
        )

        # Actions
        action_group = self.stack_sidebar.add_group(title="Actions")
        self.stack_sidebar.add_page_row(
            group=action_group,
            title="Action List",
            page_name="action_list",
            nav_page=ActionListPage(),
            prefix_icon="list-compact-symbolic",
            subtitle="Browse actions",
        )
        self.stack_sidebar.add_page_row(
            group=action_group,
            title="Action Goal",
            page_name="action_goal",
            nav_page=ActionGoalPage(),
            prefix_icon="emoji-flags-symbolic",
            subtitle="Send action goals",
        )

        # Interface
        interface_group = self.stack_sidebar.add_group(title="Interfaces")
        self.stack_sidebar.add_page_row(
            group=interface_group,
            title="Interfaces",
            page_name="interface_browser",
            nav_page=InterfaceBrowserPage(),
            prefix_icon="shapes-symbolic",
            subtitle="Browse interface definitions",
        )

        # Visualization & Control
        control_group = self.stack_sidebar.add_group(title="Control")
        self.stack_sidebar.add_page_row(
            group=control_group,
            title="Joint States",
            page_name="joint_states",
            nav_page=JointStatesPage(),
            prefix_icon="sliders-horizontal-symbolic",
            subtitle="Manipulate joints",
        )
        self.stack_sidebar.add_page_row(
            group=control_group,
            title="Teleoperator",
            page_name="teleop",
            nav_page=TeleoperatorPage(),
            prefix_icon="gamepad-symbolic",
            subtitle="Teleoperate a robot",
        )

        # Diagnostics
        diagnostics_group = self.stack_sidebar.add_group(title="Diagnostics")
        self.stack_sidebar.add_page_row(
            group=diagnostics_group,
            title="Logger",
            page_name="logger",
            nav_page=LoggerPage(),
            prefix_icon="logviewer-symbolic",
            subtitle="System logs",
        )
        self.stack_sidebar.add_page_row(
            group=diagnostics_group,
            title="Doctor",
            page_name="doctor",
            nav_page=DoctorPage(),
            prefix_icon="doctor-symbolic",
            subtitle="System diagnostics",
        )

        if self.app.settings.get_boolean("restore-last-page"):
            last_page = self.app.settings.get_string("last-page")

            if last_page and self.content_stack.get_child_by_name(last_page):
                self.content_stack.set_visible_child_name(last_page)

        # ros time
        self.time_box: Gtk.Box = builder.get_object("time_box")
        self.ros_time_lbl: Gtk.Label = builder.get_object("ros_time_lbl")
        self.ros_elapsed_time_lbl: Gtk.Label = builder.get_object("ros_elapsed_time_lbl")
        self.wall_time_lbl: Gtk.Label = builder.get_object("wall_time_lbl")
        self.wall_elapsed_time_lbl: Gtk.Label = builder.get_object("wall_elapsed_time_lbl")

        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.KeyvalTrigger.new(Gdk.KEY_comma, Gdk.ModifierType.CONTROL_MASK),
                action=Gtk.NamedAction.new("app.preferences"),
            )
        )

        # update time labels
        GLib.idle_add(self._update_time_labels)

    @property
    def current_page(self) -> Adw.NavigationPage:
        return self.content_stack.get_visible_child().get_visible_page()

    def on_preferences_dialog(self, *args):
        self.preferences_dialog = PreferencesDialog(ros2_connector=self.ros2_connector)
        self.preferences_dialog.present(self)

    def on_shortcuts_dialog(self, *args):
        # ShortcutsDialog().present(self) # TODO
        print("not implemented yet")

    def on_about_dialog(self, *args):
        self.about_dialog = Adw.AboutDialog(
            application_name="Insight",
            application_icon="insight",
            developer_name="Julian Müller",
            # developer_documentation="https://github.com/julianmueller/insight_gui",
            license_type=Gtk.License.APACHE_2_0,
            version="0.0.1",
            website="https://github.com/julianmueller/insight_gui",
        )
        self.about_dialog.add_credit_section("Development", ["Julian Müller"])
        self.about_dialog.add_credit_section("Inspiration", ["rqt", "ros2cli"])
        self.about_dialog.present(self)

    def on_stack_page_changed(self, stack: Gtk.Stack, stack_name: GObject.GParamSpec):
        # save the last page in settings
        last_page = self.content_stack.get_visible_child_name()
        if last_page != "welcome":
            self.app.settings.set_string("last-page", last_page)

        if self.split_view.get_collapsed():
            self.split_view.set_show_content(True)
        else:
            self.split_view.set_show_content(False)

    def _update_time_labels(self):
        node_is_running = self.app.lookup_action("ros2-node-is-running").get_state().get_boolean()

        # TODO add some rate limiting

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


class DetachedWindow(BaseWindow):
    __gtype_name__ = "DetachedWindow"

    def __init__(self, nav_page_class: Type, nav_page_kwargs: dict, **kwargs):
        super().__init__(**kwargs)

        super().set_destroy_with_parent(True)
        super().set_size_request(400, 300)
        super().set_default_size(400, 600)

        self.nav_view: Adw.NavigationView = Adw.NavigationView()
        super().set_content(self.nav_view)

        self.nav_page: Adw.NavigationPage = nav_page_class(**nav_page_kwargs)
        self.nav_view.add(self.nav_page)

    @property
    def current_page(self) -> Adw.NavigationPage:
        return self.nav_view.get_visible_page()
