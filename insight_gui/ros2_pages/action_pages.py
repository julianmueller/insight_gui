from operator import itemgetter

from rclpy.action import get_action_names_and_types
from ros2node.api import _is_hidden_name, get_node_names
from rclpy.action.graph import get_action_client_names_and_types_by_node, get_action_server_names_and_types_by_node

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.ros2_pages.msg_type_info_pages import ActionTypeInfoPage
from insight_gui.ros2_pages.node_pages import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class ActionListPage(Adw.NavigationPage):
    __gtype_name__ = "ActionListPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Action List")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(refresh_func=self.refresh)
        self.content_page.set_search_entry_placeholder_text("Search for actions")
        super().set_child(self.content_page)

        self.action_list_group = self.content_page.pref_page.add_group(empty_group_text="Refresh to show actions")

    def refresh(self, *args):
        if not self.ros2_connector.is_running:
            self.content_page.show_toast_w_btn(
                "ROS2 node not running", "Start Node", func=self.ros2_connector.start_node
            )
            return False

        self.action_list_group.clear()

        available_actions = sorted(get_action_names_and_types(node=self.ros2_connector.node))
        for i, (action_name, action_types) in enumerate(available_actions):
            # action_types is a list, as multiple servers can advertise different types to the same action
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(action_types) == 1:
                action_types = action_types[0]
            else:
                action_types = ", ".join(action_types)

            row = PrefRow(title=action_name, subtitle=action_types)
            # , is_hidden=action_or_service_is_hidden(action_name)) # TODO is_hidden possible for actions?
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                action_name=action_name,
                action_types=action_types,
                ros2_connector=self.ros2_connector,
            )
            self.action_list_group.add_row(row)

        if self.action_list_group.num_rows == 0:
            self.action_list_group.set_empty_group_text("No actions found. Refresh to try again.")

        return bool(self.content_page.pref_page.num_groups)


# TODO test this class, because i havent had an action in the list to look at its info
class ActionInfoPage(Adw.NavigationPage):
    __gtype_name__ = "ActionInfoPage"

    def __init__(
        self,
        action_name: str,
        action_types: str | list[str],
        nav_view: Adw.NavigationView = None,
        ros2_connector: ROS2Connector = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().set_title(f"Action <{action_name}>")

        self.action_name = action_name
        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(search_enabled=True, refresh_enabled=False)
        super().set_child(self.content_page)

        # Action Type
        action_type_group = self.content_page.pref_page.add_group(title="Action Type")

        def add_act_type_row(msg_type_full_name: str):
            msg_row = PrefRow(title=msg_type_full_name)  # , subtitle=node_full_name)
            msg_row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionTypeInfoPage,
                act_type_full_name=msg_type_full_name,
            )
            action_type_group.add_row(msg_row)

        if isinstance(action_types, str):
            add_act_type_row(action_types)
        elif isinstance(action_types, list):
            for msg_type in action_types:
                add_act_type_row(msg_type)

        # first, gather all nodes, to check which of them is a server/client of this action
        available_nodes = get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True)

        # Action Servers
        action_servers_group = self.content_page.pref_page.add_group(
            title="Action Servers", empty_group_text="action has no servers"
        )

        # Subscribers
        action_clients_group = self.content_page.pref_page.add_group(
            title="Action Clients", empty_group_text="action has no clients"
        )

        for node_name, node_namespace, node_full_name in sorted(available_nodes, key=itemgetter(0)):
            # add those nodes, that are servers to the action

            action_servers_list = get_action_server_names_and_types_by_node(
                node=self.ros2_connector.node, remote_node_name=node_name, remote_node_namespace=node_namespace
            )
            if any(self.action_name in server for server in action_servers_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    node_name=node_name,
                    node_namespace=node_namespace,
                    node_full_name=node_full_name,
                    ros2_connector=self.ros2_connector,
                )
                action_servers_group.add_row(row)

            # add those nodes, that are clients to the action
            action_clients_list = get_action_client_names_and_types_by_node(
                node=self.ros2_connector.node, remote_node_name=node_name, remote_node_namespace=node_namespace
            )
            if any(self.action_name in client for client in action_clients_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    node_name=node_name,
                    node_namespace=node_namespace,
                    node_full_name=node_full_name,
                    ros2_connector=self.ros2_connector,
                )
                action_clients_group.add_row(row)

        # add the counts as descriptions
        action_servers_group.set_description_to_row_count()
        action_clients_group.set_description_to_row_count()
