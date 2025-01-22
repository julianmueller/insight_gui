from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

from insight_gui.widgets.ros2_pages.settings_dialog import SettingsDialog
from insight_gui.widgets.ros2_pages.node_pages import NodeListPage
from insight_gui.widgets.ros2_pages.msg_type_browser_pages import (
    MessageTypeBrowserPage,
    ServiceTypeBrowserPage,
    ActionTypeBrowserPage,
)
from insight_gui.widgets.ros2_pages.pkg_pages import PackageListPage
from insight_gui.widgets.ros2_pages.topic_pages import TopicListPage
from insight_gui.widgets.ros2_pages.service_pages import ServiceListPage
from insight_gui.widgets.ros2_pages.action_pages import ActionListPage
from insight_gui.widgets.ros2_pages.tf_page import TransformsPage
from insight_gui.widgets.ros2_pages.log_pages import LoggerPage
from insight_gui.widgets.ros2_pages.doctor_page import DoctorPage

from insight_gui.utils.adw_colors import AdwAccentColor


@Gtk.Template(filename=str(Path(__file__).with_suffix(".ui")))
class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    split_view: Adw.NavigationSplitView = Gtk.Template.Child()

    nav_header_bar: Adw.HeaderBar = Gtk.Template.Child()
    refresh_btn: Gtk.Button = Gtk.Template.Child()
    pref_btn: Gtk.Button = Gtk.Template.Child()

    # content_header_bar: Adw.HeaderBar = Gtk.Template.Child()
    content_stack: Gtk.Stack = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_accent_colors()

        self.app = self.get_application()
        self.ros2_node.start_node()

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
            ros2_node=self.ros2_node,
        )
        # Topics
        self.add_stack_page(
            nav_page_class=TopicListPage,
            name="topic_list",
            title="Topic List",
            ros2_node=self.ros2_node,
        )
        self.add_stack_page(
            nav_page_class=MessageTypeBrowserPage,
            name="msg_type_browser",
            title="Message Type Browser",
            ros2_node=self.ros2_node,
        )
        # Services
        self.add_stack_page(
            nav_page_class=ServiceListPage,
            name="service_list",
            title="Service List",
            ros2_node=self.ros2_node,
        )
        self.add_stack_page(
            nav_page_class=ServiceTypeBrowserPage,
            name="srv_type_browser",
            title="Service Type Browser",
            ros2_node=self.ros2_node,
        )
        # Actions
        self.add_stack_page(
            nav_page_class=ActionListPage,
            name="action_list",
            title="Action List",
            ros2_node=self.ros2_node,
        )
        self.add_stack_page(
            nav_page_class=ActionTypeBrowserPage,
            name="action_type_browser",
            title="Action Type Browser",
            ros2_node=self.ros2_node,
        )
        # Transforms
        self.add_stack_page(
            nav_page_class=TransformsPage,
            name="tf",
            title="Transforms",
            ros2_node=self.ros2_node,
        )
        # Doctor
        self.add_stack_page(
            nav_page_class=DoctorPage,
            name="doctor",
            title="Doctor",
            ros2_node=self.ros2_node,
        )

        # Logger # TODO the logger still needs work
        # self.add_stack_page(
        #     nav_page_class=LoggerPage,
        #     name="logger",
        #     title="Logger",
        #     ros2_node=self.ros2_node,
        # )

        # Settings
        self.settings_dialog = SettingsDialog(ros2_node=self.ros2_node)

    @property
    def ros2_node(self):
        return self.app.ros2_node

    @Gtk.Template.Callback()
    def on_pref_btn_clicked(self, *args):
        self.settings_dialog.present(self)

    @Gtk.Template.Callback()
    def on_refresh_btn_clicked(self, *args):
        for stack_page in self.content_stack.get_pages():
            nav_view = stack_page.get_child()
            nav_page = nav_view.get_navigation_stack()[0]
            refresh_func = getattr(nav_page, "on_refresh", None)
            if callable(refresh_func):
                refresh_func()

    def add_stack_page(self, *, name: str, title: str, nav_page_class: type[Adw.NavigationPage], **kwargs):
        nav_view = Adw.NavigationView()
        nav_page = nav_page_class(nav_view=nav_view, **kwargs)
        nav_view.add(nav_page)
        self.content_stack.add_titled(child=nav_view, name=name, title=title)

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
