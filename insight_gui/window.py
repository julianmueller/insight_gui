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

from typing import Type

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GObject, Gtk, Adw, Gdk, Gio, GLib

from insight_gui.pages import all_pages

from insight_gui.ros2_pages.welcome_page import WelcomePage

from insight_gui.utils.adw_colors import AdwAccentColor
from insight_gui.widgets.stack_sidebar import StackSidebar


class BaseWindow(Adw.ApplicationWindow):
    __gtype_name__ = "BaseWindow"

    def __init__(self, app: Adw.Application, **kwargs):
        super().__init__(application=app, **kwargs)

        self.app: Adw.Application = app
        self.ros2_connector = app.ros2_connector

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
        page = self.current_page
        if page and getattr(page, "refreshable", False):
            page.refresh()  # TODO maybe use "use_cache=False" here? but this brings troubles with the refreshing func etc

    def on_detach(self, *args):
        page = self.current_page
        if page and getattr(page, "detachable", False):
            page.detach()

    def on_toggle_search(self, *args):
        page = self.current_page
        if page and getattr(page, "searchable", False):
            page.toggle_search()

    def on_page_trigger(self, *args):
        page = self.current_page
        trigger = getattr(page, "trigger", None)
        if callable(trigger):
            trigger()

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
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def get_dark(self):
        return Adw.StyleManager.get_default().get_dark()


class MainWindow(BaseWindow):
    __gtype_name__ = "MainWindow"

    def __init__(self, start_page_id: str = None, **kwargs):
        super().__init__(**kwargs)
        super().set_default_size(1200, 800)
        super().set_size_request(400, 500)

        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(self.app.share_dir / "window.ui"))

        self.split_view: Adw.NavigationSplitView = builder.get_object("split_view")
        super().set_content(self.split_view)

        break_point = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 800sp"))
        break_point.add_setter(self.split_view, "collapsed", True)
        super().add_breakpoint(break_point)

        self.nav_header_bar: Adw.HeaderBar = builder.get_object("nav_header_bar")
        self.overview_btn: Gtk.Button = builder.get_object("overview_btn")
        self.overview_btn.connect("clicked", self.on_overview_btn_clicked)

        self.menu_btn: Gtk.Button = builder.get_object("menu_btn")
        self.nav_views_stack: Gtk.Stack = builder.get_object("nav_views_stack")

        self.page_groups = all_pages
        self.stack_sidebar: StackSidebar = builder.get_object("stack_sidebar")
        self.stack_sidebar.set_stack(self.nav_views_stack)
        self.stack_sidebar.update_from_page_groups(self.page_groups)

        self._overview_nav_view = None

        welcome_nav_view = Adw.NavigationView()
        welcome_nav_view.add(WelcomePage())
        self.nav_views_stack.add_named(welcome_nav_view, "welcome")

        # load page from cli arg
        if start_page_id and self.open_page(start_page_id):
            pass

        # load last page, if setting is enabled
        elif self.app.settings.get_boolean("restore-last-page"):
            last_page = self.app.settings.get_string("last-page")

            if last_page and self.open_page(last_page):
                pass
            else:
                self.nav_views_stack.set_visible_child_name("welcome")

        # load welcome page per default
        else:
            self.nav_views_stack.set_visible_child_name("welcome")

        # connect so late, to not trigger when the stack is assembled
        self.nav_views_stack.connect("notify::visible-child-name", self.on_stack_page_changed)

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
        # GLib.idle_add(self._update_time_labels) # TODO

    @property
    def current_page(self) -> Adw.NavigationPage:
        return self.nav_views_stack.get_visible_child().get_visible_page()

    def on_preferences_dialog(self, *args):
        from insight_gui.ros2_pages.preferences_dialog import PreferencesDialog

        self.preferences_dialog = PreferencesDialog(ros2_connector=self.ros2_connector)
        self.preferences_dialog.present(self)

    def on_shortcuts_dialog(self, *args):
        # ShortcutsDialog().present(self) # TODO
        self.ros2_connector.log("Shortcuts dialog is not implemented yet.", level="warning")

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

    def on_overview_btn_clicked(self, *args):
        self.split_view.set_show_content(True)
        self.nav_views_stack.set_visible_child(self._ensure_overview_page())

    def _ensure_overview_page(self) -> Adw.NavigationView:
        if self._overview_nav_view:
            return self._overview_nav_view

        from insight_gui.ros2_pages.overview_page import OverviewPage

        self._overview_nav_view = Adw.NavigationView()
        self._overview_nav_view.add(OverviewPage(page_groups=self.page_groups))
        self.nav_views_stack.add_named(self._overview_nav_view, "overview")
        return self._overview_nav_view

    def open_page(self, page_id: str, *, detached: bool = False) -> bool:
        if page_id == "overview" and not detached:
            self.nav_views_stack.set_visible_child(self._ensure_overview_page())
            return True

        if detached:
            self.stack_sidebar.open_detached_page(page_id)
            return True

        nav_view = self.stack_sidebar.ensure_page(page_id)
        if not nav_view:
            return False

        self.nav_views_stack.set_visible_child(nav_view)
        return True

    def on_stack_page_changed(self, *args):
        # save the last page in settings
        last_page = self.nav_views_stack.get_visible_child_name()
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
                current_time = self.ros2_connector.ros2_node.get_clock().now()
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

    @GObject.Property(type=Adw.NavigationPage)
    def current_page(self) -> Adw.NavigationPage:
        return self.nav_view.get_visible_page()
