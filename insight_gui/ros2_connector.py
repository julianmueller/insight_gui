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
from threading import Thread, Lock, RLock
from typing import Callable, Tuple, List

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
from ros2service.api import get_service_names_and_types
from ros2param.api import (
    get_parameter_type_string,
    call_get_parameters,
    get_value,
)

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GObject, GLib, Gio

from insight_gui.models.node_item import NodeItem
from insight_gui.models.topic_item import TopicItem
from insight_gui.models.service_item import ServiceItem
from insight_gui.models.action_item import ActionItem
from insight_gui.models.parameter_item import ParameterItem
from insight_gui.utils.ros_logging import ros_log


class ROS2Connector(GObject.GObject):
    __gtype_name__ = "ROS2Connector"

    def __init__(self):
        super().__init__()
        self.app = Gio.Application.get_default()

        self._executor: MultiThreadedExecutor | None = None
        self.ros2_node: Node = None
        self.thread: Thread = None
        self._start_thread: Thread = None
        self.is_running = False
        self.is_starting = False
        self.start_time = None
        self._rpc_lock = Lock()
        self._node_lock = RLock()

    def _ensure_rclpy(self):
        if self._executor is not None:
            return

        with self._node_lock:
            if self._executor is not None:
                return

            if not rclpy.ok():
                rclpy.init(args=None)  # TODO use ROS_DOMAIN_ID here
            self._executor = MultiThreadedExecutor(num_threads=4)

    def _ensure_spin_thread(self):
        """Start the ROS2 spin thread if it is not already running."""
        if self.thread and self.thread.is_alive():
            return
        self.thread = Thread(target=self.spin, name="ros2-thread", daemon=True)
        self.thread.start()

    def _set_running_action_state(self, running: bool):
        def _set_state():
            try:
                self.app.lookup_action("ros2-node-is-running").set_state(GLib.Variant.new_boolean(running))
            except Exception:
                pass
            return GLib.SOURCE_REMOVE

        GLib.idle_add(_set_state)

    def start_node_async(self, *args, **kwargs):
        if self.is_running or self.is_starting:
            return

        self.is_starting = True
        self._start_thread = Thread(target=self._start_node_worker, name="ros2-start-thread", daemon=True)
        self._start_thread.start()

    def _start_node_worker(self):
        try:
            self.start_node()
        except Exception as exc:
            self.log(f"Failed to start ROS2 node: {exc}", level="error")
        finally:
            self.is_starting = False

    def start_node(self, *args, **kwargs):
        with self._node_lock:
            if self.is_running and self.thread and self.thread.is_alive():
                return

            self.is_starting = True
            try:
                self._ensure_rclpy()
                self.ros2_node = Node(
                    node_name=self.app.settings.get_string("gui-node-name"),
                    namespace=self.app.settings.get_string("gui-node-namespace"),
                    allow_undeclared_parameters=True,
                )
                self._executor.add_node(self.ros2_node)
                self.start_time = self.ros2_node.get_clock().now()
                self.is_running = True
                self._ensure_spin_thread()
                self.log(
                    f"Started ROS2 node '{self.ros2_node.get_fully_qualified_name()}'",
                    level="info",
                )
            finally:
                self.is_starting = False
                self._set_running_action_state(self.is_running)

    def stop_node(self, *args, **kwargs):
        if not self.is_running:
            return

        self.is_running = False
        if self.thread:
            self.thread.join()
            self.thread = None
        if self._executor and self.ros2_node:
            self._executor.remove_node(self.ros2_node)
        if self.ros2_node:
            self.log(
                f"Stopped ROS2 node '{self.ros2_node.get_fully_qualified_name()}'",
                level="info",
            )
            self.ros2_node.destroy_node()
        self.ros2_node = None
        self._set_running_action_state(False)

    def restart_node(self, *args, **kwargs):
        """Restart the ROS2 node."""
        if self.is_running:
            self.stop_node()
        self.start_node()

    def spin(self, *args, **kwargs):
        try:
            while rclpy.ok() and self.is_running:
                try:
                    self._executor.spin_once(timeout_sec=0.1)
                except ExternalShutdownException:
                    break
                except Exception as exc:
                    self.log(f"ROS2 executor spin error: {exc}", level="error")
                    time.sleep(0.1)
            return True  # Keep the timeout function/thread active

        except (KeyboardInterrupt, ExternalShutdownException):
            self.log("ROS2 shutdown requested.", level="warning")

        finally:
            self.is_running = False
            self._set_running_action_state(False)

        return False

    def shutdown(self):
        # for sub in list(self.ros2_node.subscriptions):
        #     self.ros2_node.destroy_subscription(sub)

        if self.is_running:
            self.stop_node()
        # rclpy.shutdown()

    def on_node_state_changed(self, action: Gio.Action, value: GLib.Variant):
        action.set_state(GLib.Variant.new_boolean(self.is_running))

    def set_ros_domain_id(self, domain_id: int):
        # TODO implement this using rclpy.init(args=None, domain_id=self.app.settings.get_string("...")))
        pass

    def _split_full_name(self, full_name: str) -> tuple[str, str]:
        if "/" not in full_name:
            return "/", full_name
        namespace, name = full_name.rsplit("/", 1)
        return namespace, name

    def _resource_item_from_ros_entry(
        self,
        item_type,
        full_name: str,
        type_names: List[str],
        *,
        hidden_func: Callable[[str], bool] = topic_or_service_is_hidden,
    ):
        if not type_names:
            return None

        namespace, name = self._split_full_name(full_name)
        item = item_type(
            namespace=namespace,
            name=name,
            interface_full_name=type_names[0],
            hidden=hidden_func(name),
        )
        item.type_names = list(type_names)
        return item

    def _wait_for_future(self, future, *, timeout_sec: float | None = None):
        start = time.monotonic()
        while rclpy.ok() and not future.done():
            if timeout_sec is not None and timeout_sec > 0 and (time.monotonic() - start) > timeout_sec:
                raise TimeoutError("Timed out waiting for ROS future")
            time.sleep(0.01)

        if not future.done():
            raise RuntimeError("ROS future did not complete")

        return future.result()

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
        self._wait_for_future(future, timeout_sec=timeout_sec)

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

    # Standardized ROS2 data collection methods.
    def collect_nodes(self) -> list[NodeItem]:
        """Collect available nodes as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            with self._rpc_lock:
                node_names = get_node_names(node=self.ros2_node, include_hidden_nodes=True)
            nodes = [
                NodeItem(namespace=namespace, name=name, hidden=_is_hidden_name(full_name))
                for name, namespace, full_name in node_names
            ]
            return sorted(nodes, key=lambda node: node.full_name)
        except Exception as e:
            self.log(f"Error getting nodes: {e}", level="error")
            return []

    def collect_topics(self) -> list[TopicItem]:
        """Collect available topics as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            with self._rpc_lock:
                topics = get_topic_names_and_types(node=self.ros2_node, include_hidden_topics=True)
            if not self.app.settings.get_boolean("show-action-topics"):
                topics = self._filter_action_topics(topics)

            topics_items = []
            for topic_full_name, topic_types in topics:
                topic = self._resource_item_from_ros_entry(TopicItem, topic_full_name, topic_types)
                if topic:
                    topics_items.append(topic)
            return sorted(topics_items, key=lambda topic: topic.full_name)

        except Exception as e:
            self.log(f"Error getting topics: {e}", level="error")
            return []

    def collect_publishers_by_node(self, node: NodeItem) -> list[TopicItem]:
        """Collect publishers for a specific node as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            with self._rpc_lock:
                publishers = self.ros2_node.get_publisher_names_and_types_by_node(
                    node_name=node.name, node_namespace=node.namespace
                )
            # publishers: List[Tuple(topic_full_name, List[topic_types])]
            # this function also returns service and action clients/servers of this node
            topics = []

            for topic_full_name, topic_types in publishers:
                if not topic_types or not re.search("/(msg|action)/", topic_types[0]):
                    continue

                is_action_topic = re.search(r"/_action/(status|feedback)", topic_full_name)
                if is_action_topic and not self.app.settings.get_boolean("show-action-topics"):
                    continue

                topic = self._resource_item_from_ros_entry(TopicItem, topic_full_name, topic_types)
                if topic:
                    topics.append(topic)

            return sorted(topics, key=lambda topic: topic.full_name)

        except Exception as e:
            self.log(f"Error getting publishers for node '{node.full_name}': {e}", level="error")
            return []

    def collect_subscribers_by_node(self, node: NodeItem) -> list[TopicItem]:
        """Collect subscribers for a specific node as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            with self._rpc_lock:
                subscribers = self.ros2_node.get_subscriber_names_and_types_by_node(
                    node_name=node.name, node_namespace=node.namespace
                )
            topics = []

            for topic_full_name, topic_types in subscribers:
                if not topic_types or not re.search("/(msg|action)/", topic_types[0]):
                    continue

                is_action_topic = re.search(r"/_action/(status|feedback)", topic_full_name)
                if is_action_topic and not self.app.settings.get_boolean("show-action-topics"):
                    continue

                topic = self._resource_item_from_ros_entry(TopicItem, topic_full_name, topic_types)
                if topic:
                    topics.append(topic)

            return sorted(topics, key=lambda topic: topic.full_name)

        except Exception as e:
            self.log(f"Error getting subscribers for node '{node.full_name}': {e}", level="error")
            return []

    def collect_services(self) -> list[ServiceItem]:
        """Collect available services as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            with self._rpc_lock:
                services = get_service_names_and_types(node=self.ros2_node, include_hidden_services=True)
            if not self.app.settings.get_boolean("show-action-services"):
                services = self._filter_action_services(services)
            if not self.app.settings.get_boolean("show-parameter-services"):
                services = self._filter_param_services(services)

            service_items = []
            for service_full_name, service_types in services:
                if not service_types or not re.search("/srv/", service_types[0]):
                    continue

                service = self._resource_item_from_ros_entry(ServiceItem, service_full_name, service_types)
                if service:
                    service_items.append(service)
            return sorted(service_items, key=lambda service: service.full_name)

        except Exception as e:
            self.log(f"Error getting services: {e}", level="error")
            return []

    def collect_service_clients_by_node(self, node: NodeItem) -> list[ServiceItem]:
        """Collect service clients for a specific node as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            with self._rpc_lock:
                service_clients = self.ros2_node.get_client_names_and_types_by_node(
                    node_name=node.name, node_namespace=node.namespace
                )
            services = []

            for service_full_name, service_types in service_clients:
                if not service_types or not re.search("/srv/", service_types[0]):
                    continue

                _, service_name = self._split_full_name(service_full_name)

                if not self.app.settings.get_boolean("show-parameter-services") and re.search(
                    r"/(describe_parameters|get_parameters|get_parameter_types|list_parameters|set_parameters|set_parameters_atomically|get_type_description)$",
                    service_name,
                ):
                    continue

                if not self.app.settings.get_boolean("show-action-services") and re.search(
                    r"/_action/", service_full_name
                ):
                    continue

                service = self._resource_item_from_ros_entry(ServiceItem, service_full_name, service_types)
                if service:
                    services.append(service)

            return sorted(services, key=lambda service: service.full_name)

        except Exception as e:
            self.log(f"Error getting service clients for node '{node.full_name}': {e}", level="error")
            return []

    def collect_service_servers_by_node(self, node: NodeItem) -> list[ServiceItem]:
        """Collect service servers for a specific node as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            with self._rpc_lock:
                service_servers = self.ros2_node.get_service_names_and_types_by_node(
                    node_name=node.name, node_namespace=node.namespace
                )
            services = []

            for service_full_name, service_types in service_servers:
                if not service_types or not re.search("/srv/", service_types[0]):
                    continue

                _, service_name = self._split_full_name(service_full_name)

                if not self.app.settings.get_boolean("show-parameter-services") and re.search(
                    r"/(describe_parameters|get_parameters|get_parameter_types|list_parameters|set_parameters|set_parameters_atomically|get_type_description)$",
                    service_name,
                ):
                    continue

                if not self.app.settings.get_boolean("show-action-services") and re.search(
                    r"/_action/", service_full_name
                ):
                    continue

                service = self._resource_item_from_ros_entry(ServiceItem, service_full_name, service_types)
                if service:
                    services.append(service)

            return sorted(services, key=lambda service: service.full_name)

        except Exception as e:
            self.log(f"Error getting service servers for node '{node.full_name}': {e}", level="error")
            return []

    def collect_actions(self) -> list[ActionItem]:
        """Collect available actions as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            with self._rpc_lock:
                available_actions = get_action_names_and_types(node=self.ros2_node)

            actions = []
            for action_full_name, action_types in available_actions:
                action = self._resource_item_from_ros_entry(ActionItem, action_full_name, action_types)
                if action:
                    actions.append(action)
            return sorted(actions, key=lambda action: action.full_name)

        except Exception as e:
            self.log(f"Error getting actions: {e}", level="error")
            return []

    def collect_action_clients_by_node(self, node: NodeItem) -> list[ActionItem]:
        """Collect action clients for a specific node as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            with self._rpc_lock:
                action_clients = get_action_client_names_and_types_by_node(
                    node=self.ros2_node,
                    remote_node_name=node.name,
                    remote_node_namespace=node.namespace,
                )
            actions = []

            for action_full_name, action_types in action_clients:
                if not action_types or not re.search("/action/", action_types[0]):
                    continue

                action = self._resource_item_from_ros_entry(ActionItem, action_full_name, action_types)
                if action:
                    actions.append(action)

            return sorted(actions, key=lambda action: action.full_name)

        except Exception as e:
            self.log(f"Error getting action clients for node '{node.full_name}': {e}", level="error")
            return []

    def collect_action_servers_by_node(self, node: NodeItem) -> list[ActionItem]:
        """Collect action servers for a specific node as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            with self._rpc_lock:
                action_servers = get_action_server_names_and_types_by_node(
                    node=self.ros2_node,
                    remote_node_name=node.name,
                    remote_node_namespace=node.namespace,
                )
            actions = []

            for action_full_name, action_types in action_servers:
                if not action_types or not re.search("/action/", action_types[0]):
                    continue

                action = self._resource_item_from_ros_entry(ActionItem, action_full_name, action_types)
                if action:
                    actions.append(action)

            return sorted(actions, key=lambda action: action.full_name)

        except Exception as e:
            self.log(f"Error getting action servers for node '{node.full_name}': {e}", level="error")
            return []

    def collect_parameters(self, node: NodeItem) -> list[ParameterItem]:
        """Collect parameters for a specific node as detached GObject items."""
        if not self.is_running or not self.ros2_node:
            return []

        try:
            client = AsyncParameterClient(node=self.ros2_node, remote_node_name=node.full_name)
            ready = client.wait_for_services(timeout_sec=5.0)
            if not ready:
                raise RuntimeError(
                    f"Wait for service timed out waiting for parameter services for node {node.full_name}"
                )

            # get all parameters
            future = client.list_parameters()
            response = self._wait_for_future(future, timeout_sec=5.0) if future else None
            param_names = response.result.names if response else []

            if not response:
                return []

            parameters = [ParameterItem(name=param_name, node=node) for param_name in param_names]

            # add parameter descriptions
            future = client.describe_parameters(names=param_names)
            response = self._wait_for_future(future, timeout_sec=5.0)

            if response is None:
                return []

            for param, param_descriptor in zip(parameters, response.descriptors):
                param.type = param_descriptor.type
                param.type_str = get_parameter_type_string(param_descriptor.type)
                param.read_only = param_descriptor.read_only
                param.description = param_descriptor.description
                param.dynamic_typing = param_descriptor.dynamic_typing
                param.integer_range = param_descriptor.integer_range
                param.floating_point_range = param_descriptor.floating_point_range
                param.additional_constraints = param_descriptor.additional_constraints

            # add parameter values
            future = client.get_parameters(names=param_names)
            response = self._wait_for_future(future, timeout_sec=5.0)

            if response is None:
                return []

            for param, param_value in zip(parameters, response.values):
                param.value = param_value

            # Filter out QoS parameters if requested
            # if not self.app.settings.get_boolean("show-qos-parameters"):
            #     parameters = self._filter_qos_params(parameters)

            return sorted(parameters, key=lambda param: param.name)

        except Exception as e:
            self.log(f"Error getting parameters for node '{node.full_name}': {e}", level="error")
            return []

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
            self.log(
                f"Error getting value for parameter '{parameter.name}' of node '{parameter.node.full_name}': {e}",
                level="error",
            )
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

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with the specified severity level (debug, [info], warning, error, fatal)."""
        logger = self.ros2_node.get_logger() if self.ros2_node else None
        if logger is None:
            ros_log(message, level=level)
            return

        log_func = getattr(logger, level, None)
        if log_func is None:
            logger.info(f"{level} is not a valid logging level. Defaulting to info.")
            log_func = logger.info
        log_func(str(message))
