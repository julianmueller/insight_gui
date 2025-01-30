from operator import itemgetter

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from rclpy.action.graph import get_action_client_names_and_types_by_node, get_action_server_names_and_types_by_node
from ros2node.api import _is_hidden_name, get_node_names

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_node import ROS2CommunicationNode
from insight_gui.widgets.helpers.content_page import ContentPage
from insight_gui.widgets.helpers.pref_row import PrefRow


class NodeListPage(Adw.NavigationPage):
    __gtype_name__ = "NodeListPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_node: ROS2CommunicationNode = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Node List")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_node = ros2_node if ros2_node else self.get_root().ros2_node

        self.content_page = ContentPage(refresh_func=self.refresh)
        self.content_page.set_search_entry_placeholder_text("Search for nodes")
        super().set_child(self.content_page)

        self.list_group = self.content_page.pref_page.add_group(empty_msg="No nodes found")

    def refresh(self, *args) -> bool:
        if not self.ros2_node.is_running:
            # TODO now, the msg "refresh yielded no result" shows up, make it, that refresh is restarted
            self.content_page.show_toast_w_btn("ROS2 node not running", "Start Node", func=self.ros2_node.start_node)
            return False

        self.list_group.clear()

        available_nodes = get_node_names(node=self.ros2_node.node, include_hidden_nodes=True)
        for node_name, node_namespace, node_full_name in sorted(available_nodes, key=itemgetter(0)):
            row = PrefRow(title=node_name, subtitle=node_full_name, is_hidden=_is_hidden_name(node_name))

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=NodeInfoPage,
                node_name=node_name,
                node_namespace=node_namespace,
                node_full_name=node_full_name,
                ros2_node=self.ros2_node,
            )

            self.list_group.add_row(row)

        return False  # bool(self.content_page.pref_page.num_groups)


class NodeInfoPage(Adw.NavigationPage):
    __gtype_name__ = "NodeInfoPage"

    def __init__(
        self,
        node_name: str,
        node_namespace: str,
        node_full_name: str,
        nav_view: Adw.NavigationView = None,
        ros2_node: ROS2CommunicationNode = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().set_title(f"Node '{node_full_name}'")

        self.node_name = node_name
        self.node_namespace = node_namespace
        self.node_full_name = node_full_name
        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_node = ros2_node if ros2_node else self.get_root().ros2_node

        self.content_page = ContentPage(search_enabled=True, refresh_enabled=False)
        super().set_child(self.content_page)

        # Parameters
        # TODO this is for the gui node, get it for the 'remote' node
        # parameters_group = self.content_page.pref_page.add_group(title="Parameters", description="", empty_msg="Node has no Parameters")
        #
        # parameter_list = ros2_node.list_parameters(prefixes=[], depth=5)  # rcl_interfaces.mg.ListParametersResult
        # parameter_list = list(
        #     zip(
        #         parameter_list.names,
        #         parameter_list.prefixes if len(parameter_list.prefixes) == 0 else [""] * len(parameter_list.names),
        #     )
        # )
        # for param_name, param_prefix in sorted(parameter_list, key=itemgetter(0)):
        #     row = PrefRow(title=param_name, subtitle=param_prefix)
        #     parameters_group.add_row(row)

        # Imports here, to prevent circular imports # TODO find a nicer way?
        from insight_gui.widgets.ros2_pages.topic_pages import TopicInfoPage
        from insight_gui.widgets.ros2_pages.service_pages import ServiceInfoPage
        from insight_gui.widgets.ros2_pages.action_pages import ActionInfoPage

        # Publishers
        publishers_group = self.content_page.pref_page.add_group(title="Publishers", empty_msg="Node has no publishers")

        # publisher_list = get_publisher_info(node=ros2_node, remote_node_name=node_name, include_hidden=True)
        publisher_list = self.ros2_node.node.get_publisher_names_and_types_by_node(
            node_name=node_name, node_namespace=node_namespace
        )
        for topic_name, topic_types in sorted(publisher_list, key=itemgetter(0)):
            row = PrefRow(
                title=topic_name, subtitle=", ".join(topic_types), is_hidden=topic_or_service_is_hidden(topic_name)
            )
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                topic_name=topic_name,
                topic_types=topic_types,
                ros2_node=self.ros2_node,
            )
            publishers_group.add_row(row)

        # Subscribers
        subscribers_group = self.content_page.pref_page.add_group(
            title="Subscribers", empty_msg="Node has no subscribers"
        )

        # subscriber_list = get_subscriber_info(node=ros2_node, remote_node_name=node_name, include_hidden=True)
        subscriber_list = self.ros2_node.node.get_subscriber_names_and_types_by_node(
            node_name=node_name, node_namespace=node_namespace
        )
        for topic_name, topic_types in sorted(subscriber_list, key=itemgetter(0)):
            row = PrefRow(
                title=topic_name, subtitle=", ".join(topic_types), is_hidden=topic_or_service_is_hidden(topic_name)
            )
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                topic_name=topic_name,
                topic_types=topic_types,
                ros2_node=self.ros2_node,
            )
            subscribers_group.add_row(row)

        # Service Servers
        service_servers_group = self.content_page.pref_page.add_group(
            title="Service Servers", description="", empty_msg="Node has no service servers"
        )

        # service_servers_list = get_service_server_info(node=ros2_node, remote_node_name=node_name, include_hidden=True)
        service_server_list = self.ros2_node.node.get_service_names_and_types_by_node(
            node_name=node_name, node_namespace=node_namespace
        )
        for service_name, service_types in sorted(service_server_list, key=itemgetter(0)):
            row = PrefRow(
                title=service_name,
                subtitle=", ".join(service_types),
                is_hidden=topic_or_service_is_hidden(service_name),
            )
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                service_name=service_name,
                service_types=service_types,
                ros2_node=self.ros2_node,
            )
            service_servers_group.add_row(row)

        # Service Clients
        service_clients_group = self.content_page.pref_page.add_group(
            title="Service Clients", empty_msg="Node has no service clients"
        )

        # service_clients_list = get_service_client_info(node=ros2_node, remote_node_name=node_name, include_hidden=True)
        service_client_list = self.ros2_node.node.get_client_names_and_types_by_node(
            node_name=node_name, node_namespace=node_namespace
        )
        for service_name, service_types in sorted(service_client_list, key=itemgetter(0)):
            row = PrefRow(
                title=service_name,
                subtitle=", ".join(service_types),
                is_hidden=topic_or_service_is_hidden(service_name),
            )
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                service_name=service_name,
                service_types=service_types,
                ros2_node=self.ros2_node,
            )
            service_clients_group.add_row(row)

        # Action Servers
        action_servers_group = self.content_page.pref_page.add_group(
            title="Action Servers", empty_msg="Node has no action servers"
        )

        action_servers_list = get_action_server_names_and_types_by_node(
            node=self.ros2_node.node, remote_node_name=node_name, remote_node_namespace=node_namespace
        )
        for action_name, action_types in sorted(action_servers_list, key=itemgetter(0)):
            row = PrefRow(
                title=action_name, subtitle=", ".join(action_types), is_hidden=topic_or_service_is_hidden(action_name)
            )
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                action_name=action_name,
                action_types=action_types,
                ros2_node=self.ros2_node,
            )
            action_servers_group.add_row(row)

        # Action Clients
        action_clients_group = self.content_page.pref_page.add_group(
            title="Action Clients", empty_msg="Node has no action clients"
        )

        action_clients_list = get_action_client_names_and_types_by_node(
            node=self.ros2_node.node, remote_node_name=node_name, remote_node_namespace=node_namespace
        )
        for action_name, action_types in sorted(action_clients_list, key=itemgetter(0)):
            row = PrefRow(
                title=action_name, subtitle=", ".join(action_types), is_hidden=topic_or_service_is_hidden(action_name)
            )
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                action_name=action_name,
                action_types=action_types,
                ros2_node=self.ros2_node,
            )
            action_clients_group.add_row(row)

        # add the counts as descriptions
        subscribers_group.set_description_to_row_count()
        publishers_group.set_description_to_row_count()
        service_servers_group.set_description_to_row_count()
        service_clients_group.set_description_to_row_count()
        action_servers_group.set_description_to_row_count()
        action_clients_group.set_description_to_row_count()
