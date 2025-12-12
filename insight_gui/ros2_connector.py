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
from operator import itemgetter
from functools import wraps

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
from rclpy.action.graph import get_action_client_names_and_types_by_node, get_action_server_names_and_types_by_node

# from rosidl_runtime_py.utilities import get_action

# ROS2 API imports for data collection
from ros2node.api import get_node_names, _is_hidden_name
from ros2topic.api import get_topic_names_and_types, get_msg_class
from ros2service.api import get_service_names_and_types, get_service_class
from ros2param.api import (
    call_describe_parameters,
    get_parameter_type_string,
    call_get_parameters,
    get_value,
    call_list_parameters,
)

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib, Gio

from insight_gui.utils.chache import ttl_cache
from functools import wraps, lru_cache


def cached(_func=None, *, use_ttl: bool = True):
    """Decorator that applies caching using the connector's cache settings.

    When use_ttl is False, caching uses plain lru_cache (no expiry). The wrapped
    method can be called with no_cache=True to bypass caching for that call.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            no_cache = kwargs.pop("no_cache", False)
            app_settings = getattr(getattr(self, "app", None), "settings", None)

            if (
                no_cache
                or getattr(self, "force_no_cache", False)
                or not (app_settings and app_settings.get_boolean("enable-caching"))
                or (use_ttl and getattr(self, "CACHE_TTL", 0) <= 0)
                or getattr(self, "CACHE_MAXSIZE", 0) <= 0
            ):
                return func(self, *args, **kwargs)

            if not hasattr(self, "_cache_wrappers"):
                self._cache_wrappers: Dict[Callable, Callable] = {}
            if not hasattr(self, "_cached_methods"):
                self._cached_methods: List[Callable] = []

            cached_entry = self._cache_wrappers.get(func)
            if cached_entry is None:
                if use_ttl:
                    cached_entry = ttl_cache(
                        maxsize=int(self.CACHE_MAXSIZE),
                        ttl=int(self.CACHE_TTL),
                    )(lambda *a, **k: func(self, *a, **k))
                else:
                    cached_entry = lru_cache(maxsize=int(self.CACHE_MAXSIZE))(lambda *a, **k: func(self, *a, **k))
                self._cache_wrappers[func] = cached_entry
                self._cached_methods.append(func)

            return cached_entry(*args, **kwargs)

        return wrapper

    if _func is None:
        return decorator
    return decorator(_func)


class ROS2Connector:
    def __init__(self):
        super().__init__()
        self.app = Gio.Application.get_default()

        self.node: Node = None
        self.thread: GLib.Thread = None
        self.is_running = False
        self.start_time = None
        self.CACHE_TTL = self.app.settings.get_double("cache-expiration-time")
        self.CACHE_MAXSIZE = 128
        self._cache_wrappers: Dict[Callable, Callable] = {}
        self._cached_methods: List[Callable] = []
        self._rpc_lock = threading.Lock()

        rclpy.init(args=None)

    def start_node(self, *args, **kwargs):
        if self.is_running:
            return

        # print(f"Starting ROS2 Node with name '{node_name}'")
        self.node = Node(
            node_name=self.app.settings.get_string("gui-node-name"),
            namespace=self.app.settings.get_string("gui-node-namespace"),
            allow_undeclared_parameters=True,
        )
        self.start_time = self.node.get_clock().now()
        self.thread = GLib.Thread.new("ros2-thread", self.spin, None)
        self.is_running = True
        self.app.lookup_action("ros2-node-is-running").set_state(GLib.Variant.new_boolean(True))

    def stop_node(self, *args, **kwargs):
        if not self.is_running:
            return

        self.is_running = False
        # print(f"Stopping ROS2 Node with name '{self.node.get_name()}'")
        if self.thread:
            self.thread.join()
            self.thread = None
        self.node.destroy_node()
        self.node = None
        self.app.lookup_action("ros2-node-is-running").set_state(GLib.Variant.new_boolean(False))

    def restart_node(self, *args, **kwargs):
        """Restart the ROS2 node."""
        if self.is_running:
            self.stop_node()
        self.start_node()

    def spin(self, *args, **kwargs):
        try:
            while rclpy.ok() and self.is_running:
                rclpy.spin_once(self.node, timeout_sec=0.1)
            return True  # Keep the timeout function/thread active

        except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
            print("CTRL+C detected. Shutting down ROS2 Node.")

        finally:
            # self.shutdown()
            self.is_running = False

        return False

    def shutdown(self):
        # for sub in list(self.node.subscriptions):
        #     self.node.destroy_subscription(sub)

        self.clear_cache()
        self.stop_node()
        # rclpy.shutdown()

    def on_node_state_changed(self, action: Gio.Action, value: GLib.Variant):
        action.set_state(GLib.Variant.new_boolean(self.is_running))

    def add_publisher(
        self, msg_type: MsgType, topic_name: str, qos_profile: QoSProfile | int = 10, **kwargs
    ) -> Publisher:
        if isinstance(qos_profile, int):
            qos_profile = QoSProfile(depth=qos_profile)
        return self.node.create_publisher(msg_type, topic_name, qos_profile=qos_profile)

    def destroy_publisher(self, pub: Publisher) -> bool:
        if not self.node:
            return

        if pub in list(self.node.publishers):
            return self.node.destroy_publisher(pub)
        else:
            raise RuntimeError("Publisher cannot be destroyed")
            return False

    def add_timer_callback(self, period: float, callback: Callable) -> Timer:
        return self.node.create_timer(period, callback)

    def add_subsciption(self, msg_type: MsgType, topic_name: str, callback: Callable) -> Subscription:
        return self.node.create_subscription(msg_type, topic_name, callback, 10)

    def destroy_subscription(self, sub: Subscription) -> bool:
        if not self.node:
            return

        if sub in list(self.node.subscriptions):
            return self.node.destroy_subscription(sub)
        else:
            raise RuntimeError("Subscription cannot be destroyed")
            return False

    # TODO this needs some refactoring and threading
    # from ros2service.verb.call import requester  # could also be used for that
    def call_service(
        self, srv_type: SrvType, srv_name: str, request: SrvTypeRequest, timeout_sec: int = -1
    ) -> SrvTypeResponse:
        if not self.is_running:
            return

        client = self.node.create_client(srv_type, srv_name)

        if not client.service_is_ready():
            client.wait_for_service(timeout_sec=2)

        future = client.call_async(request)
        # rclpy.spin_until_future_complete(self.node, future, timeout_sec=timeout_sec)
        start = time.monotonic()
        while not future.done():
            rclpy.spin_once(self.node, timeout_sec=0.01)
            if timeout_sec > 0 and (time.monotonic() - start) > timeout_sec:
                raise TimeoutError(f"Timeout while waiting for response from '{srv_name}'.")

        if future.result():
            return future.result()
        else:
            raise RuntimeError(f"Service call failed: {future.exception()}")

    def send_action_goal(self, action_type, action_name: str, goal, feedback_callback=None, timeout_sec: int = -1):
        """Send an action goal and return the action client for managing the goal."""
        if not self.is_running:
            return None

        action_client = ActionClient(self.node, action_type, action_name)

        if not action_client.wait_for_server(timeout_sec=2.0):
            raise RuntimeError(f"Action server '{action_name}' not available")

        goal_future = action_client.send_goal_async(goal, feedback_callback=feedback_callback)

        return action_client, goal_future

    # Cache management methods
    CACHE_TTL: float = 0.0
    CACHE_MAXSIZE: int = 128

    def _cached_functions(self) -> List[Callable]:
        return list(getattr(self, "_cache_wrappers", {}).values())

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._cache_wrappers = {}
        self._cached_methods = []

    def change_caching(self, ttl: float | None = None, maxsize: int | None = None) -> None:
        """Update cache TTL/maxsize and clear existing caches."""
        if ttl is not None:
            self.CACHE_TTL = float(ttl)
        if maxsize is not None:
            self.CACHE_MAXSIZE = int(maxsize)
        self.clear_cache()

    # Standardized ROS2 data collection methods with caching
    @cached
    def get_available_nodes(self) -> List[Tuple[str, str, str]]:
        """Get available nodes with caching support."""
        if not self.is_running or not self.node:
            return []

        try:
            nodes = get_node_names(node=self.node, include_hidden_nodes=True)
            nodes = sorted(nodes, key=itemgetter(0))

            # Filter hidden nodes if requested
            if not self.app.settings.get_boolean("show-hidden-nodes"):
                nodes = self._filter_hidden_nodes(nodes)

            return nodes

        except Exception as e:
            print(f"Error getting nodes: {e}")
            return []

    @cached
    def get_available_topics(self) -> List[Tuple[str, List[str]]]:
        """Get available topics with caching support."""
        if not self.is_running or not self.node:
            return []

        try:
            topics = get_topic_names_and_types(node=self.node, include_hidden_topics=True)
            topics = sorted(topics, key=itemgetter(0))

            # Apply filters to the data
            if not self.app.settings.get_boolean("show-hidden-topics"):
                topics = self._filter_hidden_topics(topics)

            if not self.app.settings.get_boolean("show-action-topics"):
                topics = self._filter_action_topics(topics)

            return topics

        except Exception as e:
            print(f"Error getting topics: {e}")
            return []

    @cached
    def get_publishers_by_node(self, node_name: str, node_namespace: str = "/") -> List[Tuple[str, List[str]]]:
        """Get publishers for a specific node with caching support."""
        if not self.is_running or not self.node:
            return []

        try:
            publishers = self.node.get_publisher_names_and_types_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            publishers = sorted(publishers, key=itemgetter(0))

            # Filter action-related topics if requested
            if not self.app.settings.get_boolean("show-action-topics"):
                publishers = self._filter_action_topics(publishers)

            return publishers

        except Exception as e:
            print(f"Error getting publishers for node {node_namespace}/{node_name}: {e}")
            return []

    @cached
    def get_subscribers_by_node(self, node_name: str, node_namespace: str = "/") -> List[Tuple[str, List[str]]]:
        """Get subscribers for a specific node with caching support."""
        if not self.is_running or not self.node:
            return []

        try:
            subscribers = self.node.get_subscriber_names_and_types_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            subscribers = sorted(subscribers, key=itemgetter(0))

            # Filter action-related topics if requested
            if not self.app.settings.get_boolean("show-action-topics"):
                subscribers = self._filter_action_topics(subscribers)

            return subscribers

        except Exception as e:
            print(f"Error getting subscribers for node {node_namespace}/{node_name}: {e}")
            return []

    @cached
    def get_available_services(self) -> List[Tuple[str, List[str]]]:
        """Get available services with caching support."""
        if not self.is_running or not self.node:
            return []

        try:
            services = get_service_names_and_types(node=self.node, include_hidden_services=True)
            services = sorted(services, key=itemgetter(0))

            # Filter hidden services if requested
            if not self.app.settings.get_boolean("show-hidden-services"):
                services = self._filter_hidden_services(services)

            # Filter action-related services if requested
            if not self.app.settings.get_boolean("show-action-services"):
                services = self._filter_action_services(services)

            # Filter parameter-related services if requested
            if not self.app.settings.get_boolean("show-parameter-services"):
                services = self._filter_param_services(services)

            return services

        except Exception as e:
            print(f"Error getting services: {e}")
            return []

    @cached
    def get_service_clients_by_node(self, node_name: str, node_namespace: str = "/") -> List[Tuple[str, List[str]]]:
        """Get service clients for a specific node with caching support."""
        if not self.is_running or not self.node:
            return []

        try:
            service_clients = self.node.get_client_names_and_types_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            service_clients = sorted(service_clients, key=itemgetter(0))

            # Filter action-related services if requested
            if not self.app.settings.get_boolean("show-action-services"):
                service_clients = self._filter_action_services(service_clients)

            # Filter parameter-related services if requested
            if not self.app.settings.get_boolean("show-parameter-services"):
                service_clients = self._filter_param_services(service_clients)

            return service_clients

        except Exception as e:
            print(f"Error getting service clients for node {node_namespace}/{node_name}: {e}")
            return []

    @cached
    def get_service_servers_by_node(self, node_name: str, node_namespace: str = "/") -> List[Tuple[str, List[str]]]:
        """Get service servers for a specific node with caching support."""
        if not self.is_running or not self.node:
            return []

        try:
            service_servers = self.node.get_service_names_and_types_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            service_servers = sorted(service_servers, key=itemgetter(0))

            # Filter action-related services if requested
            if not self.app.settings.get_boolean("show-action-services"):
                service_servers = self._filter_action_services(service_servers)

            # Filter parameter-related services if requested
            if not self.app.settings.get_boolean("show-parameter-services"):
                service_servers = self._filter_param_services(service_servers)

            return service_servers

        except Exception as e:
            print(f"Error getting service servers for node {node_namespace}/{node_name}: {e}")
            return []

    @cached
    def get_available_actions(self) -> List[Tuple[str, List[str]]]:
        """Get available actions with caching support."""
        if not self.is_running or not self.node:
            return []

        try:
            actions = get_action_names_and_types(node=self.node)
            actions = sorted(actions, key=itemgetter(0))

            # Filter hidden actions if requested
            if not self.app.settings.get_boolean("show-hidden-actions"):
                actions = self._filter_hidden_actions(actions)

            return actions

        except Exception as e:
            print(f"Error getting actions: {e}")
            return []

    @cached
    def get_action_clients_by_node(self, node_name: str, node_namespace: str = "/") -> List[Tuple[str, List[str]]]:
        """Get action clients for a specific node with caching support."""
        if not self.is_running or not self.node:
            return []

        try:
            action_clients = get_action_client_names_and_types_by_node(
                node=self.node, remote_node_name=node_name, remote_node_namespace=node_namespace
            )
            action_clients = sorted(action_clients, key=itemgetter(0))

            # Filter hidden actions if requested
            if not self.app.settings.get_boolean("show-hidden-actions"):
                action_clients = self._filter_hidden_actions(action_clients)

            return action_clients

        except Exception as e:
            print(f"Error getting action clients for node {node_namespace}/{node_name}: {e}")
            return []

    @cached
    def get_action_servers_by_node(self, node_name: str, node_namespace: str = "/") -> List[Tuple[str, List[str]]]:
        """Get action servers for a specific node with caching support."""
        if not self.is_running or not self.node:
            return []

        try:
            action_servers = get_action_server_names_and_types_by_node(
                node=self.node, remote_node_name=node_name, remote_node_namespace=node_namespace
            )
            action_servers = sorted(action_servers, key=itemgetter(0))

            # Filter hidden actions if requested
            if not self.app.settings.get_boolean("show-hidden-actions"):
                action_servers = self._filter_hidden_actions(action_servers)

            return action_servers

        except Exception as e:
            print(f"Error getting action servers for node {node_namespace}/{node_name}: {e}")
            return []

    # Node-specific parameter methods with caching
    @cached
    def get_parameters_by_node(self, node_name: str) -> List[str]:
        """Get parameters for a specific node with caching support."""
        return []  # FIXME

        if not self.is_running or not self.node:
            return []

        try:
            with self._rpc_lock:
                future = call_list_parameters(node=self.node, node_name=node_name)
            response = future.result() if future else None
            parameters = response.result.names if response else []
            parameters = sorted(parameters)

            # Filter out QoS parameters if requested
            if not self.app.settings.get_boolean("show-qos-parameters"):
                parameters = self._filter_qos_params(parameters)

            return parameters

        except Exception as e:
            print(f"Error getting parameters for node {node_name}: {e}")
            return []

    # @cached
    def get_parameter_value(self, node_name: str, parameter_name: str) -> Any:
        """Get parameter value for a specific parameter with caching support."""
        return None  # FIXME

        if not self.is_running or not self.node:
            return None

        try:
            with self._rpc_lock:
                values = call_get_parameters(
                    node=self.node, node_name=node_name, parameter_names=[parameter_name]
                ).values
            param_value = get_value(parameter_value=values[0]) if values else None

            return param_value

        except Exception as e:
            print(f"Error getting parameter value for {node_name}/{parameter_name}: {e}")
            return None

    @cached
    def get_parameter_type(self, node_name: str, parameter_name: str) -> str:
        """Get parameter type for a specific parameter with caching support."""
        return ""  # FIXME

        if not self.is_running or not self.node:
            return ""

        try:
            with self._rpc_lock:
                descriptors = call_describe_parameters(
                    node=self.node, node_name=node_name, parameter_names=[parameter_name]
                ).descriptors

            if not descriptors:
                return ""

            param_type = get_parameter_type_string(descriptors[0].type)

            return param_type

        except Exception as e:
            print(f"Error getting parameter type for {node_name}/{parameter_name}: {e}")
            return ""

    # @cached
    def get_parameter_info(self, node_name: str, parameter_name: str) -> Dict[str, Any]:
        """Get complete parameter information (type and value) with caching support."""
        return {"type": "", "value": None, "read_only": False}  # FIXME

        if not self.is_running or not self.node:
            return {"type": "", "value": None, "read_only": False}

        try:
            with self._rpc_lock:
                descriptors = call_describe_parameters(
                    node=self.node, node_name=node_name, parameter_names=[parameter_name]
                ).descriptors

            if not descriptors:
                return {"type": "", "value": None, "read_only": False}

            param_descriptor = descriptors[0]
            param_type = get_parameter_type_string(param_descriptor.type)
            param_read_only = getattr(param_descriptor, "read_only", False)

            with self._rpc_lock:
                values = call_get_parameters(
                    node=self.node, node_name=node_name, parameter_names=[parameter_name]
                ).values

            param_value = get_value(parameter_value=values[0]) if values else None

            param_info = {"type": param_type, "value": param_value, "read_only": param_read_only}

            return param_info

        except Exception as e:
            print(f"Error getting parameter info for {node_name}/{parameter_name}: {e}")
            return {"type": "", "value": None, "read_only": False}

    # Message and service class methods with caching
    @cached(use_ttl=False)
    def get_message_class(self, topic_name: str) -> Any:
        """Get message class for a specific topic with caching support."""
        if not self.is_running or not self.node:
            return None

        try:
            msg_class = get_msg_class(node=self.node, topic=topic_name, include_hidden_topics=True)

            return msg_class

        except Exception as e:
            print(f"Error getting message class for topic {topic_name}: {e}")
            return None

    @cached(use_ttl=False)
    def get_service_class(self, service_name: str) -> Any:
        """Get service class for a specific service with caching support."""
        if not self.is_running or not self.node:
            return None

        try:
            srv_class = get_service_class(node=self.node, service_name=service_name, include_hidden_services=True)

            return srv_class

        except Exception as e:
            print(f"Error getting service class for service {service_name}: {e}")
            return None

    @cached(use_ttl=False)
    def get_action_class(self, action_name: str) -> Any:
        """Get action class for a specific action with caching support."""
        if not self.is_running or not self.node:
            return None

        try:
            available_actions = self.get_available_actions()
            action_type = None
            for name, types in available_actions:
                if name == action_name:
                    action_type = types[0] if types else None
                    break

            if not action_type:
                return None

            package_name, interface_type, action_name_only = action_type.split("/")
            module_name = f"{package_name}.{interface_type}"

            module = importlib.import_module(module_name)
            return getattr(module, action_name_only)

        except Exception as e:
            print(f"Error getting action class for action {action_name}: {e}")
            return None

    # Utility methods for message/service type names # TODO refactor to get_interface_type_name?
    @cached(use_ttl=False)
    def get_message_type_name(self, msg_class) -> str:
        """Get the full type name for a message class (e.g., 'geometry_msgs/msg/Twist')."""
        if not msg_class:
            return ""

        try:
            # The message class has the type information in its module
            module_name = msg_class.__module__
            parts = module_name.split(".")
            if len(parts) >= 3:
                package_name = parts[0]
                interface_type = parts[1]  # 'msg', 'srv', 'action'
                message_name = msg_class.__name__
                return f"{package_name}/{interface_type}/{message_name}"
            else:
                # Fallback for edge cases
                return f"{msg_class.__module__}.{msg_class.__name__}"

        except Exception as e:
            print(f"Error getting message type name: {e}")
            # Fallback implementation
            module_name = msg_class.__module__
            package_name = module_name.split(".")[0]
            message_type = module_name.split(".")[1] if len(module_name.split(".")) > 1 else "msg"
            message_name = msg_class.__name__
            return f"{package_name}/{message_type}/{message_name}"

    @cached(use_ttl=False)
    def get_service_type_name(self, srv_class) -> str:
        """Get the full type name for a service class (e.g., 'std_srvs/srv/Empty')."""
        if not srv_class:
            return ""

        try:
            # Service classes have the same module structure as messages
            module_name = srv_class.__module__
            parts = module_name.split(".")
            if len(parts) >= 3:
                package_name = parts[0]
                interface_type = parts[1]  # should be 'srv'
                service_name = srv_class.__name__
                return f"{package_name}/{interface_type}/{service_name}"
            else:
                # Fallback for edge cases
                return f"{srv_class.__module__}.{srv_class.__name__}"

        except Exception as e:
            print(f"Error getting service type name: {e}")
            # Fallback implementation
            module_name = srv_class.__module__
            package_name = module_name.split(".")[0]
            service_type = module_name.split(".")[1] if len(module_name.split(".")) > 1 else "srv"
            service_name = srv_class.__name__
            return f"{package_name}/{service_type}/{service_name}"

    @cached(use_ttl=False)
    def get_action_type_name(self, action_class) -> str:
        """Get the full type name for an action class (e.g., 'example_interfaces/action/Fibonacci')."""
        if not action_class:
            return ""

        try:
            # Action classes have the same module structure as messages
            module_name = action_class.__module__
            parts = module_name.split(".")
            if len(parts) >= 3:
                package_name = parts[0]
                interface_type = parts[1]  # should be 'action'
                action_name = action_class.__name__
                return f"{package_name}/{interface_type}/{action_name}"
            else:
                # Fallback for edge cases
                return f"{action_class.__module__}.{action_class.__name__}"
        except Exception as e:
            print(f"Error getting action type name: {e}")
            # Fallback implementation
            module_name = action_class.__module__
            package_name = module_name.split(".")[0]
            action_type = module_name.split(".")[1] if len(module_name.split(".")) > 1 else "action"
            action_name = action_class.__name__
            return f"{package_name}/{action_type}/{action_name}"

    # Helper methods for filtering
    def _filter_hidden_nodes(self, nodes: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
        """Filter out hidden nodes from a list of nodes."""
        return [(name, namespace, full_name) for name, namespace, full_name in nodes if not _is_hidden_name(name)]

    def _filter_hidden_topics(self, items: List[Tuple[str, List[str]]]) -> List[Tuple[str, List[str]]]:
        """Filter out hidden topics from a list."""
        return [(name, types) for name, types in items if not topic_or_service_is_hidden(name)]

    def _filter_hidden_services(self, items: List[Tuple[str, List[str]]]) -> List[Tuple[str, List[str]]]:
        """Filter out hidden services from a list."""
        return [(name, types) for name, types in items if not topic_or_service_is_hidden(name)]

    # TODO check if actions can actually be hidden, as the used function is "designed" for topics and services
    def _filter_hidden_actions(self, items: List[Tuple[str, List[str]]]) -> List[Tuple[str, List[str]]]:
        """Filter out hidden actions from a list."""
        return [(name, types) for name, types in items if not topic_or_service_is_hidden(name)]

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

    def refresh_all_caches(self) -> None:
        """Force refresh all caches."""
        self.clear_cache()

        # Pre-populate caches with fresh data
        self.get_available_nodes()
        self.get_available_topics()
        self.get_available_services()
        self.get_available_actions()

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with the specified severity level (debug, [info], warning, error, fatal)."""
        if level == "info":
            self.node.get_logger().info(message)
        elif level == "warning":
            self.node.get_logger().warning(message)
        elif level == "error":
            self.node.get_logger().error(message)
        elif level == "fatal":
            self.node.get_logger().fatal(message)
        elif level == "debug":
            self.node.get_logger().debug(message)
        else:
            self.node.get_logger().info(f"{level} is not a valid logging level. Defaulting to info.")
            self.node.get_logger().info(message)
