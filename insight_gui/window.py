from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio, GLib

from insight_gui.ros2_pages.node_pages import NodeListPage
from insight_gui.ros2_pages.msg_type_browser_pages import (
    MessageTypeBrowserPage,
    ServiceTypeBrowserPage,
    ActionTypeBrowserPage,
)
from insight_gui.ros2_pages.pkg_pages import PackageListPage
from insight_gui.ros2_pages.topic_pages import TopicListPage
from insight_gui.ros2_pages.service_pages import ServiceListPage
from insight_gui.ros2_pages.service_call_page import ServiceCallPage
from insight_gui.ros2_pages.action_pages import ActionListPage
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

    time_box: Gtk.Box = Gtk.Template.Child()
    ros_time_lbl: Gtk.Label = Gtk.Template.Child()
    ros_elapsed_time_lbl: Gtk.Label = Gtk.Template.Child()
    wall_time_lbl: Gtk.Label = Gtk.Template.Child()
    wall_elapsed_time_lbl: Gtk.Label = Gtk.Template.Child()
    # TODO also add the boxes?

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_accent_colors()

        self.app = self.get_application()
        self.ros2_connector.start_node()

        self.refresh_btn.set_visible(False)  # TODO do i still need this?

        # content of the stack
        # TODO add separator lines in the stack_switcher
        self.add_stack_page(
            nav_page_class=PackageListPage,
            name="pkg_list",
            title="Package List",
        )
        self.add_stack_page(
            nav_page_class=NodeListPage,
            name="node_list",
            title="Node List",
            ros2_connector=self.ros2_connector,
        )
        # Topics
        self.add_stack_page(
            nav_page_class=TopicListPage,
            name="topic_list",
            title="Topic List",
            ros2_connector=self.ros2_connector,
        )
        self.add_stack_page(
            nav_page_class=MessageTypeBrowserPage,
            name="msg_type_browser",
            title="Message Type Browser",
            ros2_connector=self.ros2_connector,
        )
        # Services
        self.add_stack_page(
            nav_page_class=ServiceListPage,
            name="service_list",
            title="Service List",
            ros2_connector=self.ros2_connector,
        )
        self.add_stack_page(
            nav_page_class=ServiceTypeBrowserPage,
            name="srv_type_browser",
            title="Service Type Browser",
            ros2_connector=self.ros2_connector,
        )
        self.add_stack_page(
            nav_page_class=ServiceCallPage,
            name="srv_caller",
            title="Service Caller",
            ros2_connector=self.ros2_connector,
        )
        # Actions
        self.add_stack_page(
            nav_page_class=ActionListPage,
            name="action_list",
            title="Action List",
            ros2_connector=self.ros2_connector,
        )
        self.add_stack_page(
            nav_page_class=ActionTypeBrowserPage,
            name="action_type_browser",
            title="Action Type Browser",
            ros2_connector=self.ros2_connector,
        )
        # Parameters
        self.add_stack_page(
            nav_page_class=ParameterListPage,
            name="param_list",
            title="Parameters",
            ros2_connector=self.ros2_connector,
        )
        # Transforms
        self.add_stack_page(
            nav_page_class=TransformsPage,
            name="tf",
            title="Transforms",
            ros2_connector=self.ros2_connector,
        )
        # Images
        self.add_stack_page(
            nav_page_class=ImageViewerPage,
            name="img_viewer",
            title="Image Viewer",
            ros2_connector=self.ros2_connector,
        )
        # Joint States
        self.add_stack_page(
            nav_page_class=JointStatesPage,
            name="joint_states",
            title="Joint States",
            ros2_connector=self.ros2_connector,
        )
        # Logger
        self.add_stack_page(
            nav_page_class=LoggerPage,
            name="logger",
            title="Logger",
            ros2_connector=self.ros2_connector,
        )
        # Doctor
        self.add_stack_page(
            nav_page_class=DoctorPage,
            name="doctor",
            title="Doctor",
            ros2_connector=self.ros2_connector,
        )

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

        # TODO add shortcuts
        # action = Gio.SimpleAction.new("shortcuts", None)
        # action.connect("activate", lambda *_: self.shortcuts_dialog.present(self))
        # self.app.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", lambda *_: self.about_dialog.present(self))
        self.app.add_action(action)

        action = Gio.SimpleAction.new_stateful(
            "ros2_node_state",  # Action name (used in menus, shortcuts, etc.)
            None,  # No parameter is needed for a boolean toggle.
            GLib.Variant.new_boolean(self.ros2_connector.is_running),  # Initial state.
        )
        action.connect("change-state", self.ros2_connector.on_node_state_changed)
        # action.connect("notify::state", self.update_time_labels)
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
                action=Gtk.CallbackAction.new(self.on_dedock_shortcut),
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

    def on_dedock_shortcut(self, *args):
        self.content_stack.get_visible_child().get_visible_page().on_dedock()

    def add_stack_page(self, *, name: str, title: str, nav_page_class: type[Adw.NavigationPage], **kwargs):
        nav_view = Adw.NavigationView()
        nav_page = nav_page_class(nav_view=nav_view, **kwargs)
        nav_view.add(nav_page)
        self.content_stack.add_titled(child=nav_view, name=name, title=title)

    def update_time_labels(self):
        # current_state = action.get_state().get_boolean()
        # print("current state is", current_state)
        action = self.app.lookup_action("ros2_node_state")
        node_is_running = action.get_state().get_boolean() if action is not None else False

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
