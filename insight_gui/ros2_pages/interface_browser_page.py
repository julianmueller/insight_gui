import subprocess

from rosidl_runtime_py import (
    get_message_interfaces,
    get_service_interfaces,
    get_action_interfaces,
    get_interface_path,
)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.ros2_pages.msg_type_info_pages import (
    MessageTypeInfoPage,
    ServiceTypeInfoPage,
    ActionTypeInfoPage,
)
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow


class InterfaceBrowserPage(Adw.NavigationPage):
    __gtype_name__ = "InterfaceBrowserPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Interface Browser")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(empty_page_text="Refresh to show message types")
        self.content_page.set_search_entry_placeholder_text("Search for message types")
        self.content_page.set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})
        super().set_child(self.content_page)

    def refresh(self, *args) -> bool:
        self.content_page.pref_page.clear()

        available_msgs = get_message_interfaces()

        for pkg_name, msgs_list in sorted(available_msgs.items()):
            msg_group = self.content_page.pref_page.add_group(title=pkg_name)

            for msg in sorted(msgs_list):
                msg_type_full_name = f"{pkg_name}/{msg}"
                msg_type = msg.removeprefix("msg/")  # remove namespace

                row = PrefRow(title=msg_type, subtitle=msg_type_full_name)

                # row.add_suffix_btn(
                #     icon_name="info-symbolic",
                #     tooltip_text="Message Info",
                #     func=self.on_get_msg_info,
                #     func_kwargs={"msg_type_full_name": msg_type_full_name},
                # )
                # row.add_suffix_btn(
                #     icon_name="folder-symbolic",
                #     tooltip_text="Open Message File",
                #     func=_on_open_msg_file,
                #     func_kwargs={"msg_type_full_name": msg_type_full_name},
                # )
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=MessageTypeInfoPage,
                    msg_type_full_name=msg_type_full_name,
                )
                msg_group.add_row(row)

        if len(available_msgs) == 0:
            self.content_page.pref_page.set_empty_page_text("No topics found. Refresh to try again.")

        return bool(self.content_page.pref_page.num_groups)


class ServiceTypeBrowserPage(Adw.NavigationPage):
    __gtype_name__ = "ServiceTypeBrowserPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Service Type Browser")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(empty_page_text="Refresh to show service types")
        self.content_page.set_search_entry_placeholder_text("Search for service types")
        self.content_page.set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})
        super().set_child(self.content_page)

    def refresh(self, *args) -> bool:
        self.content_page.pref_page.clear()

        available_srvs = get_service_interfaces()

        # TODO
        for pkg_name, srvs_list in sorted(available_srvs.items()):
            srv_group = self.content_page.pref_page.add_group(title=pkg_name)

            for srv in sorted(srvs_list):
                srv_type_full_name = f"{pkg_name}/{srv}"
                srv_type = srv.removeprefix("srv/")  # remove namespace

                row = PrefRow(title=srv_type, subtitle=srv_type_full_name)

                # row.add_suffix_btn(
                #     icon_name="info-symbolic",
                #     tooltip_text="Message Info",
                #     func=self.on_get_msg_info,
                #     func_kwargs={"msg_type_full_name": msg_type_full_name},
                # )
                # row.add_suffix_btn(
                #     icon_name="folder-symbolic",
                #     tooltip_text="Open Message File",
                #     func=_on_open_msg_file,
                #     func_kwargs={"msg_type_full_name": msg_type_full_name},
                # )
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=ServiceTypeInfoPage,
                    srv_type_full_name=srv_type_full_name,
                )
                srv_group.add_row(row)

        if len(available_srvs) == 0:
            self.content_page.pref_page.set_empty_page_text("No Services found. Refresh to try again.")

        return bool(self.content_page.pref_page.num_groups)


class ActionTypeBrowserPage(Adw.NavigationPage):
    __gtype_name__ = "ActionTypeBrowserPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Action Type Browser")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(empty_page_text="Refresh to show action types")
        self.content_page.set_search_entry_placeholder_text("Search for action types")
        self.content_page.set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})
        super().set_child(self.content_page)

    def refresh(self, *args) -> bool:
        self.content_page.pref_page.clear()

        available_action_msgs = get_action_interfaces()
        for pkg_name, actions_list in sorted(available_action_msgs.items()):
            actions_group = self.content_page.pref_page.add_group(title=pkg_name)

            for act in sorted(actions_list):
                act_type_full_name = f"{pkg_name}/{act}"
                act_type = act.removeprefix("msg/")  # remove namespace

                row = PrefRow(title=act_type, subtitle=act_type_full_name)

                # row.add_suffix_btn(
                #     icon_name="info-symbolic",
                #     tooltip_text="Message Info",
                #     func=self.on_get_msg_info,
                #     func_kwargs={"msg_type_full_name": msg_type_full_name},
                # )
                # row.add_suffix_btn(
                #     icon_name="folder-symbolic",
                #     tooltip_text="Open Message File",
                #     func=_on_open_msg_file,
                #     func_kwargs={"msg_type_full_name": msg_type_full_name},
                # )
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=ActionTypeInfoPage,
                    act_type_full_name=act_type_full_name,
                )
                actions_group.add_row(row)

        if len(available_action_msgs) == 0:
            self.content_page.pref_page.set_empty_page_text("No actions found. Refresh to try again.")

        return bool(self.content_page.pref_page.num_groups)


def _on_open_msg_file(btn: Gtk.Button = None, *, msg_type_full_name: str):
    msg_file_path = get_interface_path(msg_type_full_name)
    # i: ignore session
    subprocess.Popen(["gnome-text-editor", msg_file_path, "--ignore-session"])
    # os.system(f"gnome-text-editor {msg_file_path} -ins")
