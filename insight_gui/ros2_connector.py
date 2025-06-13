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

from typing import Callable, Dict, Any, Tuple, List
from operator import itemgetter
import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.publisher import Publisher, MsgType
from rclpy.subscription import Subscription
from rclpy.service import Service, SrvType, SrvTypeRequest, SrvTypeResponse
from rclpy.timer import Timer

# ROS2 API imports for data collection
from ros2topic.api import get_topic_names_and_types
from ros2node.api import get_node_names
from ros2service.api import get_service_names_and_types
from rclpy.action import get_action_names_and_types
from rclpy.action.graph import get_action_client_names_and_types_by_node, get_action_server_names_and_types_by_node

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib, Gio


class ROS2Connector:
    def __init__(self, application, cache_timeout: float = 5.0):
        super().__init__()
        self.app = application

        self.node: Node = None
        self.thread: GLib.Thread = None
        self.is_running = False
        self.start_time = None

        # Cache system
        self.cache_timeout = cache_timeout  # Cache timeout in seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

        rclpy.init(args=None)

    def start_node(self, node_name: str = "insight_gui", *args, **kwargs):
        if self.is_running:
            return

        print(f"Starting ROS2 Node with name '{node_name}'")
        self.node = Node(node_name=node_name)
        self.start_time = self.node.get_clock().now()
        self.thread = GLib.Thread.new("ros2-thread", self.spin, None)
        self.is_running = True
        self.app.lookup_action("ros2-node-is-running").set_state(GLib.Variant.new_boolean(True))

    def stop_node(self):
        if not self.is_running:
            return

        self.is_running = False
        print(f"Stopping ROS2 Node with name '{self.node.get_name()}'")
        if self.thread:
            self.thread.join()
            self.thread = None
        self.node.destroy_node()
        self.node = None
        self.app.lookup_action("ros2-node-is-running").set_state(GLib.Variant.new_boolean(False))

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

    def on_node_state_changed(self, action: Gio.Action, value: GLib.Variant):
        action.set_state(GLib.Variant.new_boolean(self.is_running))

    def add_publisher(self, msg_type: MsgType, topic_name: str, queue_size: int = 10) -> Publisher:
        return self.node.create_publisher(msg_type, topic_name, queue_size)

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

    def shutdown(self):
        for sub in list(self.node.subscriptions):
            self.node.destroy_subscription(sub)

        # Clear cache on shutdown
        with self._cache_lock:
            self._cache.clear()

        # self.is_running = False
        self.stop_node()
        # rclpy.shutdown()
        print("Shutting down ROS2 Node.")

    # Cache management methods
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid based on timeout."""
        if cache_key not in self._cache:
            return False

        cache_entry = self._cache[cache_key]
        current_time = time.time()
        return (current_time - cache_entry["timestamp"]) < self.cache_timeout

    def _get_from_cache(self, cache_key: str) -> Any:
        """Get data from cache if valid, otherwise return None."""
        with self._cache_lock:
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]["data"]
            return None

    def _store_in_cache(self, cache_key: str, data: Any) -> None:
        """Store data in cache with current timestamp."""
        with self._cache_lock:
            self._cache[cache_key] = {"data": data, "timestamp": time.time()}

    def clear_cache(self, cache_key: str = None) -> None:
        """Clear cache. If cache_key is provided, clear only that entry, otherwise clear all."""
        with self._cache_lock:
            if cache_key:
                self._cache.pop(cache_key, None)
            else:
                self._cache.clear()

    def set_cache_timeout(self, timeout: float) -> None:
        """Set the cache timeout in seconds."""
        self.cache_timeout = timeout

    # Standardized ROS2 data collection methods with caching
    def get_available_nodes(self, include_hidden: bool = True, use_cache: bool = True) -> List[Tuple[str, str, str]]:
        """Get available nodes with caching support."""
        if not self.is_running or not self.node:
            return []

        cache_key = f"nodes{'_hidden' if include_hidden else ''}"

        if use_cache:
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        try:
            nodes = get_node_names(node=self.node, include_hidden_nodes=include_hidden)
            nodes = sorted(nodes, key=itemgetter(0))  # Sort by node name

            if use_cache:
                self._store_in_cache(cache_key, nodes)

            return nodes
        except Exception as e:
            print(f"Error getting nodes: {e}")
            return []

    def get_available_topics(self, include_hidden: bool = True, use_cache: bool = True) -> List[Tuple[str, List[str]]]:
        """Get available topics with caching support."""
        if not self.is_running or not self.node:
            return []

        cache_key = f"topics{'_hidden' if include_hidden else ''}"

        if use_cache:
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        try:
            topics = get_topic_names_and_types(node=self.node, include_hidden_topics=include_hidden)
            topics = sorted(topics, key=itemgetter(0))  # Sort by topic name

            if use_cache:
                self._store_in_cache(cache_key, topics)

            return topics
        except Exception as e:
            print(f"Error getting topics: {e}")
            return []

    def get_available_services(
        self, include_hidden: bool = True, use_cache: bool = True
    ) -> List[Tuple[str, List[str]]]:
        """Get available services with caching support."""
        if not self.is_running or not self.node:
            return []

        cache_key = f"services{'_hidden' if include_hidden else ''}"

        if use_cache:
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        try:
            services = get_service_names_and_types(node=self.node, include_hidden_services=include_hidden)
            services = sorted(services, key=itemgetter(0))  # Sort by service name

            if use_cache:
                self._store_in_cache(cache_key, services)

            return services
        except Exception as e:
            print(f"Error getting services: {e}")
            return []

    def get_available_actions(self, use_cache: bool = True) -> List[Tuple[str, List[str]]]:
        """Get available actions with caching support."""
        if not self.is_running or not self.node:
            return []

        cache_key = "actions"

        if use_cache:
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        try:
            actions = get_action_names_and_types(node=self.node)
            actions = sorted(actions, key=lambda x: x[0])  # Sort by action name

            if use_cache:
                self._store_in_cache(cache_key, actions)

            return actions
        except Exception as e:
            print(f"Error getting actions: {e}")
            return []

    # Convenience methods for cache management
    def refresh_nodes_cache(self, include_hidden: bool = True) -> List[Tuple[str, str, str]]:
        """Force refresh nodes cache and return new data."""
        cache_key = f"nodes_hidden_{include_hidden}"
        self.clear_cache(cache_key)
        return self.get_available_nodes(include_hidden=include_hidden, use_cache=True)

    def refresh_topics_cache(self, include_hidden: bool = True) -> List[Tuple[str, List[str]]]:
        """Force refresh topics cache and return new data."""
        cache_key = f"topics_hidden_{include_hidden}"
        self.clear_cache(cache_key)
        return self.get_available_topics(include_hidden=include_hidden, use_cache=True)

    def refresh_services_cache(self, include_hidden: bool = True) -> List[Tuple[str, List[str]]]:
        """Force refresh services cache and return new data."""
        cache_key = f"services_hidden_{include_hidden}"
        self.clear_cache(cache_key)
        return self.get_available_services(include_hidden=include_hidden, use_cache=True)

    def refresh_actions_cache(self) -> List[Tuple[str, List[str]]]:
        """Force refresh actions cache and return new data."""
        cache_key = "actions"
        self.clear_cache(cache_key)
        return self.get_available_actions(use_cache=True)

    # Node-specific action methods with caching
    def get_action_clients_by_node(
        self, node_name: str, node_namespace: str = "/", use_cache: bool = True
    ) -> List[Tuple[str, List[str]]]:
        """Get action clients for a specific node with caching support."""
        if not self.is_running or not self.node:
            return []

        cache_key = f"action_clients_{node_namespace}_{node_name}"

        if use_cache:
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        try:
            action_clients = get_action_client_names_and_types_by_node(
                node=self.node, remote_node_name=node_name, remote_node_namespace=node_namespace
            )
            action_clients = sorted(action_clients, key=lambda x: x[0])  # Sort by action name

            if use_cache:
                self._store_in_cache(cache_key, action_clients)

            return action_clients
        except Exception as e:
            print(f"Error getting action clients for node {node_namespace}/{node_name}: {e}")
            return []

    def get_action_servers_by_node(
        self, node_name: str, node_namespace: str = "/", use_cache: bool = True
    ) -> List[Tuple[str, List[str]]]:
        """Get action servers for a specific node with caching support."""
        if not self.is_running or not self.node:
            return []

        cache_key = f"action_servers_{node_namespace}_{node_name}"

        if use_cache:
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        try:
            action_servers = get_action_server_names_and_types_by_node(
                node=self.node, remote_node_name=node_name, remote_node_namespace=node_namespace
            )
            action_servers = sorted(action_servers, key=lambda x: x[0])  # Sort by action name

            if use_cache:
                self._store_in_cache(cache_key, action_servers)

            return action_servers
        except Exception as e:
            print(f"Error getting action servers for node {node_namespace}/{node_name}: {e}")
            return []

    def refresh_action_clients_cache(self, node_name: str, node_namespace: str = "/") -> List[Tuple[str, List[str]]]:
        """Force refresh action clients cache for a specific node and return new data."""
        cache_key = f"action_clients_{node_namespace}_{node_name}"
        self.clear_cache(cache_key)
        return self.get_action_clients_by_node(node_name=node_name, node_namespace=node_namespace, use_cache=True)

    def refresh_action_servers_cache(self, node_name: str, node_namespace: str = "/") -> List[Tuple[str, List[str]]]:
        """Force refresh action servers cache for a specific node and return new data."""
        cache_key = f"action_servers_{node_namespace}_{node_name}"
        self.clear_cache(cache_key)
        return self.get_action_servers_by_node(node_name=node_name, node_namespace=node_namespace, use_cache=True)

    def refresh_all_caches(self) -> None:
        """Force refresh all caches."""
        self.clear_cache()
        # Pre-populate caches with fresh data
        self.get_available_nodes(include_hidden=True, use_cache=True)
        self.get_available_nodes(include_hidden=False, use_cache=True)
        self.get_available_topics(include_hidden=True, use_cache=True)
        self.get_available_topics(include_hidden=False, use_cache=True)
        self.get_available_services(include_hidden=True, use_cache=True)
        self.get_available_services(include_hidden=False, use_cache=True)
        self.get_available_actions(use_cache=True)
