# =============================================================================
# ros2_connector.py
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

import re
import time
import threading
import importlib
from typing import Callable, Dict, Any, Tuple, List

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from rclpy.publisher import Publisher, MsgType
from rclpy.subscription import Subscription
from rclpy.service import Service, SrvType, SrvTypeRequest, SrvTypeResponse
from rclpy.timer import Timer
from rclpy.action import ActionClient
from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from rclpy.action import get_action_names_and_types
from rclpy.action.graph import (
    get_action_client_names_and_types_by_node,
    get_action_server_names_and_types_by_node,
)
from rclpy.parameter_client import AsyncParameterClient
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor

# from rosidl_runtime_py.utilities import get_action

# ROS2 API imports for data collection # TODO replace all of them with rclpy implementations
from ros2node.api import get_node_names, _is_hidden_name
from ros2topic.api import get_topic_names_and_types  # , get_msg_class
from ros2service.api import get_service_names_and_types  # , get_service_class
from ros2param.api import (
    call_describe_parameters,
    get_parameter_type_string,
    call_get_parameters,
    get_value,
    call_list_parameters,
)

import gi

gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import GObject, GLib, Gio, Gtk

from insight_gui.models.node_item import NodeItem
from insight_gui.models.topic_item import TopicItem
from insight_gui.models.service_item import ServiceItem
from insight_gui.models.action_item import ActionItem
from insight_gui.models.interface_item import (
    InterfaceTypeItem,
    TopicInterfaceTypeItem,
    ServiceInterfaceTypeItem,
    ActionInterfaceTypeItem,
)
from insight_gui.models.parameter_item import ParameterItem


class ROS2Connector(GObject.GObject):
    __gtype_name__ = "ROS2Connector"

    nodes_store = GObject.Property(type=Gio.ListStore)
    topics_store = GObject.Property(type=Gio.ListStore)
    services_store = GObject.Property(type=Gio.ListStore)
    actions_store = GObject.Property(type=Gio.ListStore)
    interfaces_store = GObject.Property(type=Gio.ListStore)
    parameters_store = GObject.Property(type=Gio.ListStore)
    pkgs_store = GObject.Property(type=Gio.ListStore)  # TODO use this

    def __init__(self):
        super().__init__()
        self.app = Gio.Application.get_default()
        rclpy.init(args=None)  # TODO use ROS_DOMAIN_ID here

        self._executor = MultiThreadedExecutor(num_threads=4)
        self.ros2_node: Node = None
        self.thread: GLib.Thread = None
        self.is_running = False
        self.start_time = None
        self._rpc_lock = threading.Lock()

    def start_node(self, *args, **kwargs):
        if self.is_running:
            return

        # print(f"Starting ROS2 Node with name '{node_name}'")
        self.ros2_node = Node(
            node_name=self.app.settings.get_string("gui-node-name"),
            namespace=self.app.settings.get_string("gui-node-namespace"),
            allow_undeclared_parameters=True,
        )
        self._executor.add_node(self.ros2_node)
        self.start_time = self.ros2_node.get_clock().now()
        self.thread = GLib.Thread.new("ros2-thread", self.spin, None)
        self.is_running = True
        self.app.lookup_action("ros2-node-is-running").set_state(GLib.Variant.new_boolean(True))

    def stop_node(self, *args, **kwargs):
        if not self.is_running:
            return

        self.is_running = False
        # print(f"Stopping ROS2 Node with name '{self.ros2_node.get_name()}'")
        if self.thread:
            self.thread.join()
            self.thread = None
        self.ros2_node.destroy_node()
        self.ros2_node = None
        self.app.lookup_action("ros2-node-is-running").set_state(GLib.Variant.new_boolean(False))

    def restart_node(self, *args, **kwargs):
        """Restart the ROS2 node."""
        if self.is_running:
            self.stop_node()
        self.start_node()

    def spin(self, *args, **kwargs):
        try:
            while rclpy.ok() and self.is_running:
                rclpy.spin_once(self.ros2_node, executor=self._executor, timeout_sec=0.1)
            return True  # Keep the timeout function/thread active

        except (KeyboardInterrupt, ExternalShutdownException):
            print("CTRL+C detected. Shutting down ROS2 Node.")

        finally:
            # self.shutdown()
            self.is_running = False

        return False

    def shutdown(self):
        # for sub in list(self.ros2_node.subscriptions):
        #     self.ros2_node.destroy_subscription(sub)

        self.stop_node()
        # rclpy.shutdown()

    def on_node_state_changed(self, action: Gio.Action, value: GLib.Variant):
        action.set_state(GLib.Variant.new_boolean(self.is_running))

    def set_ros_domain_id(self, domain_id: int):
        # TODO implement this using rclpy.init(args=None, domain_id=self.app.settings.get_string("...")))
        pass

    def add_publisher(
        self,
        msg_type: MsgType,
        topic_name: str,
        qos_profile: QoSProfile | int = 10,
        **kwargs,
    ) -> Publisher:
        if isinstance(qos_profile, int):
            qos_profile = QoSProfile(depth=qos_profile)
        return self.ros2_node.create_publisher(msg_type, topic_name, qos_profile=qos_profile)

    def destroy_publisher(self, pub: Publisher) -> bool:
        if not self.ros2_node:
            return

        if pub in list(self.ros2_node.publishers):
            return self.ros2_node.destroy_publisher(pub)
        else:
            raise RuntimeError("Publisher cannot be destroyed")
            return False

    def add_timer_callback(self, period: float, callback: Callable) -> Timer:
        return self.ros2_node.create_timer(period, callback)

    def add_subsciption(self, msg_type: MsgType, topic_name: str, callback: Callable) -> Subscription:
        return self.ros2_node.create_subscription(msg_type, topic_name, callback, 10)

    def destroy_subscription(self, sub: Subscription) -> bool:
        if not self.ros2_node:
            return

        if sub in list(self.ros2_node.subscriptions):
            return self.ros2_node.destroy_subscription(sub)
        else:
            raise RuntimeError("Subscription cannot be destroyed")
            return False

    # TODO this needs some refactoring and threading
    # from ros2service.verb.call import requester  # could also be used for that
    def call_service(
        self,
        srv_type: SrvType,
        srv_name: str,
        request: SrvTypeRequest,
        timeout_sec: int = -1,
    ) -> SrvTypeResponse:
        if not self.is_running:
            return

        client = self.ros2_node.create_client(srv_type, srv_name)

        if not client.service_is_ready():
            client.wait_for_service(timeout_sec=2)

        future = client.call_async(request)
        # rclpy.spin_until_future_complete(self.ros2_node, future, timeout_sec=timeout_sec)
        start = time.monotonic()
        while not future.done():
            rclpy.spin_once(self.ros2_node, timeout_sec=0.01)
            if timeout_sec > 0 and (time.monotonic() - start) > timeout_sec:
                raise TimeoutError(f"Timeout while waiting for response from '{srv_name}'.")

        if future.result():
            return future.result()
        else:
            raise RuntimeError(f"Service call failed: {future.exception()}")

    def send_action_goal(
        self,
        action_type,
        action_name: str,
        goal,
        feedback_callback=None,
        timeout_sec: int = -1,
    ):
        """Send an action goal and return the action client for managing the goal."""
        if not self.is_running:
            return None

        action_client = ActionClient(self.ros2_node, action_type, action_name)

        if not action_client.wait_for_server(timeout_sec=2.0):
            raise RuntimeError(f"Action server '{action_name}' not available")

        goal_future = action_client.send_goal_async(goal, feedback_callback=feedback_callback)

        return action_client, goal_future

    # Standardized ROS2 data collection methods with caching
    def get_available_nodes(self) -> Gio.ListStore:
        """Get available nodes with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        nodes = Gio.ListStore.new(NodeItem)

        try:
            node_names = get_node_names(node=self.ros2_node, include_hidden_nodes=True)
            # returned as a List['name', 'namespace', 'full_name']

            for name, namespace, full_name in node_names:
                n = NodeItem(
                    namespace=namespace,
                    name=name,
                    hidden=_is_hidden_name(full_name),
                )
                nodes.append(n)

            nodes.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return nodes

        except Exception as e:
            print(f"Error getting nodes: {e}")
            return Gio.ListStore()

    def get_available_topics(self) -> Gio.ListStore:
        """Get available topics with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        try:
            topics = get_topic_names_and_types(node=self.ros2_node, include_hidden_topics=True)
            if not self.app.settings.get_boolean("show-action-topics"):
                topics = self._filter_action_topics(topics)
            topics_store = Gio.ListStore.new(TopicItem)

            for topic_full_name, topic_types in topics:
                topic_namespace, topic_name = topic_full_name.rsplit("/", 1)
                topic = TopicItem(
                    name=topic_name,
                    namespace=topic_namespace,
                    interface_full_name=topic_types[0],
                    hidden=topic_or_service_is_hidden(topic_name),
                )

                # TODO move this in the appropriate gui place
                # if not self.app.settings.get_boolean("show-hidden-topics") and item.hidden:
                #     continue
                # if not self.app.settings.get_boolean("show-action-topics") and item.is_action_topic:
                #     continue

                topics_store.append(topic)

            topics_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return topics_store

        except Exception as e:
            print(f"Error getting topics: {e}")
            return Gio.ListStore()

    def get_publishers_by_node(self, node: NodeItem) -> Gio.ListStore:
        """Get publishers for a specific node with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        try:
            publishers = self.ros2_node.get_publisher_names_and_types_by_node(
                node_name=node.name, node_namespace=node.namespace
            )
            # publishers: List[Tuple(topic_full_name, List[topic_types])]
            # this function also returns service and action clients/servers of this node
            publisher_store = Gio.ListStore.new(TopicItem)

            for topic_full_name, topic_types in publishers:
                if not re.search("/(msg|action)/", topic_types[0]):
                    continue

                topic_namespace, topic_name = topic_full_name.rsplit("/", 1)

                is_action_topic = re.search(r"/_action/(status|feedback)", topic_full_name)
                if is_action_topic and not self.app.settings.get_boolean("show-action-topics"):
                    continue

                topic = TopicItem(
                    name=topic_name,
                    namespace=topic_namespace,
                    interface_full_name=topic_types[0],
                    hidden=topic_or_service_is_hidden(topic_name),
                )

                publisher_store.append(topic)

            publisher_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return publisher_store

        except Exception as e:
            print(f"Error getting publishers for node '{node.full_name}': {e}")
            return Gio.ListStore()

    def get_subscribers_by_node(self, node: NodeItem) -> Gio.ListStore:
        """Get subscribers for a specific node with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        try:
            subscribers = self.ros2_node.get_subscriber_names_and_types_by_node(
                node_name=node.name, node_namespace=node.namespace
            )
            subscriber_store = Gio.ListStore.new(TopicItem)

            for topic_full_name, topic_types in subscribers:
                if not re.search("/(msg|action)/", topic_types[0]):
                    continue

                topic_namespace, topic_name = topic_full_name.rsplit("/", 1)

                is_action_topic = re.search(r"/_action/(status|feedback)", topic_full_name)
                if is_action_topic and not self.app.settings.get_boolean("show-action-topics"):
                    continue

                topic = TopicItem(
                    name=topic_name,
                    namespace=topic_namespace,
                    interface_full_name=topic_types[0],
                    hidden=topic_or_service_is_hidden(topic_name),
                )

                # TODO move this in the appropriate gui place
                # if not self.app.settings.get_boolean("show-action-topics") and toppic.is_action_topic:
                #     continue

                subscriber_store.append(topic)

            subscriber_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return subscriber_store

        except Exception as e:
            print(f"Error getting subscribers for node '{node.full_name}': {e}")
            return Gio.ListStore()

    def get_available_services(self) -> Gio.ListStore:
        """Get available services with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        try:
            services = get_service_names_and_types(node=self.ros2_node, include_hidden_services=True)
            if not self.app.settings.get_boolean("show-action-services"):
                services = self._filter_action_services(services)
            if not self.app.settings.get_boolean("show-parameter-services"):
                services = self._filter_param_services(services)
            service_store = Gio.ListStore.new(ServiceItem)

            for service_full_name, service_types in services:
                service_namespace, service_name = service_full_name.rsplit("/", 1)
                if not re.search("/srv/", service_types[0]):
                    continue

                service = ServiceItem(
                    name=service_name,
                    namespace=service_namespace,
                    interface_full_name=service_types[0],
                    hidden=topic_or_service_is_hidden(service_name),
                )

                # TODO move this in the appropriate gui place
                # if not self.app.settings.get_boolean("show-hidden-services") and service.hidden:
                #     continue
                # if not self.app.settings.get_boolean("show-action-services") and service.is_action_service:
                #     continue
                # if not self.app.settings.get_boolean("show-parameter-services") and service.is_parameter_service:
                #     continue

                service_store.append(service)

            service_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return service_store

        except Exception as e:
            print(f"Error getting services: {e}")
            return Gio.ListStore()

    def get_service_clients_by_node(self, node: NodeItem) -> Gio.ListStore:
        """Get service clients for a specific node with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        try:
            service_clients = self.ros2_node.get_client_names_and_types_by_node(
                node_name=node.name, node_namespace=node.namespace
            )
            client_store = Gio.ListStore.new(ServiceItem)

            for service_full_name, service_types in service_clients:
                if not re.search("/srv/", service_types[0]):
                    continue

                service_namespace, service_name = service_full_name.rsplit("/", 1)

                if not self.app.settings.get_boolean("show-parameter-services") and re.search(
                    r"/(describe_parameters|get_parameters|get_parameter_types|list_parameters|set_parameters|set_parameters_atomically|get_type_description)$",
                    service_name,
                ):
                    continue

                if not self.app.settings.get_boolean("show-action-services") and re.search(r"/_action/", service_name):
                    continue

                service = ServiceItem(
                    name=service_name,
                    namespace=service_namespace,
                    interface_full_name=service_types[0],
                    hidden=topic_or_service_is_hidden(service_name),
                )

                # TODO move this in the appropriate gui place
                # if not self.app.settings.get_boolean("show-action-services") and service.is_action_service:
                #     continue

                # if not self.app.settings.get_boolean("show-parameter-services") and service.is_parameter_service:
                #     continue

                client_store.append(service)

            client_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return client_store

        except Exception as e:
            print(f"Error getting service clients for node '{node.full_name}': {e}")
            return Gio.ListStore()

    def get_service_servers_by_node(self, node: NodeItem) -> Gio.ListStore:
        """Get service servers for a specific node with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        try:
            service_servers = self.ros2_node.get_service_names_and_types_by_node(
                node_name=node.name, node_namespace=node.namespace
            )
            server_store = Gio.ListStore.new(ServiceItem)

            for service_full_name, service_types in service_servers:
                if not re.search("/srv/", service_types[0]):
                    continue

                service_namespace, service_name = service_full_name.rsplit("/", 1)

                if not self.app.settings.get_boolean("show-parameter-services") and re.search(
                    r"/(describe_parameters|get_parameters|get_parameter_types|list_parameters|set_parameters|set_parameters_atomically|get_type_description)$",
                    service_name,
                ):
                    continue

                if not self.app.settings.get_boolean("show-action-services") and re.search(r"/_action/", service_name):
                    continue

                service = ServiceItem(
                    name=service_name,
                    namespace=service_namespace,
                    interface_full_name=service_types[0],
                    hidden=topic_or_service_is_hidden(service_name),
                )

                # TODO move this in the appropriate gui place
                # if not self.app.settings.get_boolean("show-action-services") and service.is_action_service:
                #     continue
                # if not self.app.settings.get_boolean("show-parameter-services") and service.is_parameter_service:
                #     continue

                server_store.append(service)

            server_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return server_store

        except Exception as e:
            print(f"Error getting service servers for node '{node.full_name}': {e}")
            return Gio.ListStore()

    def get_available_actions(self) -> Gio.ListStore:
        """Get available actions with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        try:
            available_actions = get_action_names_and_types(node=self.ros2_node)
            action_store = Gio.ListStore.new(ActionItem)

            for action_full_name, action_types in available_actions:
                action_namespace, action_name = action_full_name.rsplit("/", 1)
                action = ActionItem(
                    name=action_name,
                    namespace=action_namespace,
                    interface_full_name=action_types[0],
                    hidden=topic_or_service_is_hidden(action_name),
                )

                # TODO move this in the appropriate gui place
                # if not self.app.settings.get_boolean("show-hidden-actions") and action.hidden:
                #     continue

                action_store.append(action)

            action_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return action_store

        except Exception as e:
            print(f"Error getting actions: {e}")
            return Gio.ListStore()

    def get_action_clients_by_node(self, node: NodeItem) -> Gio.ListStore:
        """Get action clients for a specific node with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        try:
            action_clients = get_action_client_names_and_types_by_node(
                node=self.ros2_node,
                remote_node_name=node.name,
                remote_node_namespace=node.namespace,
            )
            client_store = Gio.ListStore.new(ActionItem)

            for action_full_name, action_types in action_clients:
                if not re.search("/action/", action_types[0]):
                    continue

                action_namespace, action_name = action_full_name.rsplit("/", 1)
                action = ActionItem(
                    name=action_name,
                    namespace=action_namespace,
                    interface_full_name=action_types[0],
                    hidden=topic_or_service_is_hidden(action_name),
                )

                # TODO move this in the appropriate gui place
                # if not self.app.settings.get_boolean("show-hidden-actions") and item.hidden:
                #     continue

                client_store.append(action)

            client_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return client_store

        except Exception as e:
            print(f"Error getting action clients for node '{node.full_name}': {e}")
            return Gio.ListStore()

    def get_action_servers_by_node(self, node: NodeItem) -> Gio.ListStore:
        """Get action servers for a specific node with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        try:
            action_servers = get_action_server_names_and_types_by_node(
                node=self.ros2_node,
                remote_node_name=node.name,
                remote_node_namespace=node.namespace,
            )
            server_store = Gio.ListStore.new(ActionItem)

            for action_full_name, action_types in action_servers:
                if not re.search("/action/", action_types[0]):
                    continue

                action_namespace, action_name = action_full_name.rsplit("/", 1)
                action = ActionItem(
                    name=action_name,
                    namespace=action_namespace,
                    interface_full_name=action_types[0],
                    hidden=topic_or_service_is_hidden(action_name),
                )

                # TODO move this in the appropriate gui place
                # if not self.app.settings.get_boolean("show-hidden-actions") and action.hidden:
                #     continue

                server_store.append(action)

            server_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return server_store

        except Exception as e:
            print(f"Error getting action servers for node '{node.full_name}': {e}")
            return Gio.ListStore()

    # Node-specific parameter methods with caching
    def get_parameters_by_node(self, node: NodeItem) -> Gio.ListStore:
        """Get parameters for a specific node with caching support."""
        if not self.is_running or not self.ros2_node:
            return Gio.ListStore()

        try:
            parameters: Gio.ListStore = Gio.ListStore.new(ParameterItem)

            client = AsyncParameterClient(node=self.ros2_node, remote_node_name=node.full_name)
            ready = client.wait_for_services(timeout_sec=5.0)
            if not ready:
                raise RuntimeError(
                    f"Wait for service timed out waiting for parameter services for node {node.full_name}"
                )
                return Gio.ListStore()

            # get all parameters
            future = client.list_parameters()
            rclpy.spin_until_future_complete(node=self.ros2_node, future=future)
            response = future.result() if future else None
            param_names = response.result.names

            if not response:
                return Gio.ListStore()

            for param_descriptor in param_names:
                param = ParameterItem(name=param_descriptor, node=node)
                parameters.append(param)

            # add parameter descriptions
            future = client.describe_parameters(names=param_names)
            rclpy.spin_until_future_complete(node=self.ros2_node, future=future)
            response = future.result()

            if response is None:
                return Gio.ListStore()

            for param, param_descriptor in zip(parameters, response.descriptors):
                param.type = param_descriptor.type  # get_parameter_type_string(param_descriptor.type)
                param.type_str = get_parameter_type_string(param_descriptor.type)
                param.read_only = param_descriptor.read_only
                param.description = param_descriptor.description
                param.dynamic_typing = param_descriptor.dynamic_typing
                param.integer_range = param_descriptor.integer_range
                param.floating_point_range = param_descriptor.floating_point_range
                param.additional_constraints = param_descriptor.additional_constraints
                # success = self.update_parameter_info(param)
                # if not success:
                #     print(f"could not update param {param.name}")

            # add parameter values
            future = client.get_parameters(names=param_names)
            rclpy.spin_until_future_complete(node=self.ros2_node, future=future)
            response = future.result()

            if response is None:
                return Gio.ListStore()

            for param, param_value in zip(parameters, response.values):
                param.value = param_value  # TODO why is this always None??

            # parameters = response.result.names if response else []
            # parameters = sorted(parameters)

            # Filter out QoS parameters if requested
            # if not self.app.settings.get_boolean("show-qos-parameters"):
            #     parameters = self._filter_qos_params(parameters)

            # for param in parameters:
            #     parameters.append(Gtk.StringObject.new(name))

            parameters.sort(compare_func=lambda a, b: (a.name > b.name) - (a.name < b.name))
            return parameters

        except Exception as e:
            print(f"Error getting parameters for node '{node.full_name}': {e}")
            return Gio.ListStore()

    def get_parameter_value(self, parameter: ParameterItem) -> object | None:
        """Get parameter value for a specific parameter with caching support."""
        if not self.is_running or not self.ros2_node:
            return None

        try:
            values = call_get_parameters(
                node=self.ros2_node,
                node_name=parameter.node.name,
                parameter_names=[parameter.name],
                # TODO maybe change this function, so it loads all parameters at once, instead of one at a time?
            ).values
            param_value = get_value(parameter_value=values[0]) if values else None
            return param_value

        except Exception as e:
            print(f"Error getting value for parameter '{parameter.name}' of node '{parameter.node.full_name}': {e}")
            return None

    # def get_parameter_type(self, parameter: ParameterItem) -> str | None:
    #     """Get parameter type for a specific parameter with caching support."""
    #     if not self.is_running or not self.ros2_node:
    #         return None

    #     try:
    #         with self._rpc_lock:
    #             descriptors = call_describe_parameters(
    #                 node=self.ros2_node,
    #                 node_name=parameter.node.name,
    #                 parameter_names=[parameter.name],
    #                 # TODO maybe change this function, so it loads all parameters at once, instead of one at a time?
    #             ).descriptors

    #         param_type = get_parameter_type_string(descriptors[0].type) if descriptors else None
    #         return param_type

    #     except Exception as e:
    #         print(f"Error getting type for parameter '{parameter.name}' of node '{parameter.node.full_name}': {e}")
    #         return None

    # Helper methods for filtering
    def _filter_action_topics(self, topics: List[Tuple[str, List[str]]]) -> List[Tuple[str, List[str]]]:
        """Filter out action-related topics from a list of topics."""
        return [(name, types) for name, types in topics if not re.search(r"/_action/(status|feedback)", name)]

    def _filter_action_services(self, services: List[Tuple[str, List[str]]]) -> List[Tuple[str, List[str]]]:
        """Filter out action-related services from a list of services."""
        return [
            (name, types)
            for name, types in services
            if not re.search(r"/_action/(cancel_goal|get_result|send_goal)", name)
        ]

    def _filter_param_services(self, services: List[Tuple[str, List[str]]]) -> List[Tuple[str, List[str]]]:
        """Filter out parameter-related services from a list of services."""
        return [
            (name, types)
            for name, types in services
            if not re.search(
                r"/(describe_parameters|get_parameters|get_parameter_types|list_parameters|set_parameters|set_parameters_atomically|get_type_description)",
                name,
            )
        ]

    def _filter_qos_params(self, params: List[Tuple[str, List[str]]]) -> List[Tuple[str, List[str]]]:
        """Filter out QoS parameter topics from a list of topics."""
        return [name for name in params if not re.search(r"qos_overrides./", name)]

    def refresh_all_stores(self) -> None:
        """Force refresh all stores."""

        # Pre-populate stores with fresh data
        self.get_available_nodes()
        self.get_available_topics()
        self.get_available_services()
        self.get_available_actions()

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with the specified severity level (debug, [info], warning, error, fatal)."""
        if level == "info":
            self.ros2_node.get_logger().info(message)
        elif level == "warning":
            self.ros2_node.get_logger().warning(message)
        elif level == "error":
            self.ros2_node.get_logger().error(message)
        elif level == "fatal":
            self.ros2_node.get_logger().fatal(message)
        elif level == "debug":
            self.ros2_node.get_logger().debug(message)
        else:
            self.ros2_node.get_logger().info(f"{level} is not a valid logging level. Defaulting to info.")
            self.ros2_node.get_logger().info(message)
