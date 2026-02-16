# =============================================================================
# ros2_dummy.py
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

import random
import re
import time
from concurrent.futures import Future
from threading import Lock
from types import SimpleNamespace
from typing import Callable, Dict, Any, Tuple, List

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


class _DummyTime:
    def __init__(self, nanoseconds: int):
        self.nanoseconds = int(nanoseconds)

    @classmethod
    def from_seconds(cls, seconds: float) -> "_DummyTime":
        return cls(int(seconds * 1e9))

    def seconds_nanoseconds(self) -> Tuple[int, int]:
        sec = self.nanoseconds // 1_000_000_000
        nanosec = self.nanoseconds % 1_000_000_000
        return sec, nanosec

    def to_msg(self):
        sec, nanosec = self.seconds_nanoseconds()
        return SimpleNamespace(sec=sec, nanosec=nanosec)

    def __sub__(self, other: "_DummyTime") -> "_DummyTime":
        if not isinstance(other, _DummyTime):
            return _DummyTime(self.nanoseconds)
        return _DummyTime(self.nanoseconds - other.nanoseconds)


def _resolved_future(result: Any) -> Future:
    future = Future()
    future.set_result(result)
    return future


class ROS2ConnectorDummy(GObject.GObject):
    __gtype_name__ = "ROS2Dummy"
    __gsignals__ = {
        "nodes-refreshed": (GObject.SignalFlags.RUN_FIRST, None, (Gio.ListStore,)),
        "topics-refreshed": (GObject.SignalFlags.RUN_FIRST, None, (Gio.ListStore,)),
        "services-refreshed": (GObject.SignalFlags.RUN_FIRST, None, (Gio.ListStore,)),
        "actions-refreshed": (GObject.SignalFlags.RUN_FIRST, None, (Gio.ListStore,)),
        "parameters-refreshed": (GObject.SignalFlags.RUN_FIRST, None, (Gio.ListStore,)),
    }

    nodes_store = GObject.Property(type=Gio.ListStore)
    topics_store = GObject.Property(type=Gio.ListStore)
    services_store = GObject.Property(type=Gio.ListStore)
    actions_store = GObject.Property(type=Gio.ListStore)
    interfaces_store = GObject.Property(type=Gio.ListStore)
    parameters_store = GObject.Property(type=Gio.ListStore)
    pkgs_store = GObject.Property(type=Gio.ListStore)  # TODO use this

    _DEFAULT_NODE_COUNT = 25
    _DEFAULT_TOPIC_COUNT = 120
    _DEFAULT_SERVICE_COUNT = 40
    _DEFAULT_ACTION_COUNT = 12
    _DEFAULT_PARAM_COUNT = 18

    _PARAM_TYPE_CODES = {
        "not_set": 0,
        "bool": 1,
        "integer": 2,
        "double": 3,
        "string": 4,
        "byte_array": 5,
        "bool_array": 6,
        "integer_array": 7,
        "double_array": 8,
        "string_array": 9,
    }

    _NAMESPACE_ROOTS = [
        "/",
        "/robot1",
        "/robot2",
        "/robot3",
        "/nav",
        "/perception",
        "/sensors",
        "/manipulator",
        "/localization",
        "/mapping",
        "/simulation",
        "/world",
    ]

    _NAMESPACE_SUFFIXES = [
        "camera",
        "lidar",
        "imu",
        "front",
        "rear",
        "left",
        "right",
        "base",
        "arm",
        "gripper",
        "depth",
        "color",
    ]

    _NODE_NAME_POOL = [
        "controller_manager",
        "robot_state_publisher",
        "joint_state_broadcaster",
        "rviz2",
        "map_server",
        "amcl",
        "slam_toolbox",
        "ekf_filter",
        "nav2_bt_navigator",
        "behavior_server",
        "planner_server",
        "controller_server",
        "recoveries_server",
        "lifecycle_manager",
        "camera_driver",
        "lidar_driver",
        "imu_filter",
        "diagnostics_aggregator",
        "teleop_twist_joy",
        "joy_node",
        "tf_broadcaster",
        "static_tf_broadcaster",
        "image_proc",
        "pointcloud_to_laserscan",
        "laser_filters",
        "state_estimator",
        "velocity_smoother",
        "dwb_controller",
        "map_updater",
    ]

    _TOPIC_POOL = [
        ("cmd_vel", "geometry_msgs/msg/Twist"),
        ("odom", "nav_msgs/msg/Odometry"),
        ("tf", "tf2_msgs/msg/TFMessage"),
        ("tf_static", "tf2_msgs/msg/TFMessage"),
        ("scan", "sensor_msgs/msg/LaserScan"),
        ("image_raw", "sensor_msgs/msg/Image"),
        ("camera_info", "sensor_msgs/msg/CameraInfo"),
        ("map", "nav_msgs/msg/OccupancyGrid"),
        ("amcl_pose", "geometry_msgs/msg/PoseWithCovarianceStamped"),
        ("goal_pose", "geometry_msgs/msg/PoseStamped"),
        ("joint_states", "sensor_msgs/msg/JointState"),
        ("diagnostics", "diagnostic_msgs/msg/DiagnosticArray"),
        ("battery_state", "sensor_msgs/msg/BatteryState"),
        ("imu", "sensor_msgs/msg/Imu"),
        ("pose", "geometry_msgs/msg/Pose"),
        ("pose_array", "geometry_msgs/msg/PoseArray"),
        ("path", "nav_msgs/msg/Path"),
        ("clock", "rosgraph_msgs/msg/Clock"),
        ("parameter_events", "rcl_interfaces/msg/ParameterEvent"),
        ("rosout", "rcl_interfaces/msg/Log"),
        ("cmd_vel_stamped", "geometry_msgs/msg/TwistStamped"),
        ("odom_combined", "geometry_msgs/msg/PoseWithCovarianceStamped"),
        ("initialpose", "geometry_msgs/msg/PoseWithCovarianceStamped"),
        ("particle_cloud", "geometry_msgs/msg/PoseArray"),
        ("global_costmap/costmap", "nav2_msgs/msg/Costmap"),
        ("local_costmap/costmap", "nav2_msgs/msg/Costmap"),
        ("map_metadata", "nav_msgs/msg/MapMetaData"),
        ("clicked_point", "geometry_msgs/msg/PointStamped"),
        ("cmd_vel_raw", "geometry_msgs/msg/Twist"),
        ("joy", "sensor_msgs/msg/Joy"),
    ]

    _SERVICE_POOL = [
        ("trigger", "std_srvs/srv/Trigger"),
        ("set_bool", "std_srvs/srv/SetBool"),
        ("empty", "std_srvs/srv/Empty"),
        ("reset_odometry", "std_srvs/srv/Empty"),
        ("clear_costmap", "nav2_msgs/srv/ClearEntireCostmap"),
        ("load_map", "nav2_msgs/srv/LoadMap"),
        ("save_map", "nav2_msgs/srv/SaveMap"),
        ("set_initial_pose", "nav2_msgs/srv/SetInitialPose"),
        ("get_plan", "nav_msgs/srv/GetPlan"),
        ("set_pose", "nav_msgs/srv/SetMap"),
        ("set_parameters", "rcl_interfaces/srv/SetParameters"),
        ("get_parameters", "rcl_interfaces/srv/GetParameters"),
    ]

    _ACTION_POOL = [
        ("navigate_to_pose", "nav2_msgs/action/NavigateToPose"),
        ("follow_waypoints", "nav2_msgs/action/FollowWaypoints"),
        ("spin", "nav2_msgs/action/Spin"),
        ("backup", "nav2_msgs/action/BackUp"),
        ("drive_on_heading", "nav2_msgs/action/DriveOnHeading"),
        ("wait", "nav2_msgs/action/Wait"),
        ("compute_path_to_pose", "nav2_msgs/action/ComputePathToPose"),
    ]

    _PARAM_POOL = [
        ("use_sim_time", "bool"),
        ("publish_tf", "bool"),
        ("update_rate", "double"),
        ("frequency", "double"),
        ("controller_frequency", "double"),
        ("max_vel_x", "double"),
        ("min_vel_x", "double"),
        ("max_vel_theta", "double"),
        ("frame_id", "string"),
        ("base_frame_id", "string"),
        ("odom_frame_id", "string"),
        ("map_frame_id", "string"),
        ("global_frame", "string"),
        ("robot_description", "string"),
        ("qos_overrides./tf.publisher.depth", "integer"),
        ("qos_overrides./tf_static.publisher.durability", "string"),
        ("sensor_timeout", "double"),
        ("transform_tolerance", "double"),
        ("goal_checker_xy_goal_tolerance", "double"),
        ("goal_checker_yaw_goal_tolerance", "double"),
    ]

    def __init__(self):
        super().__init__()
        self.app = Gio.Application.get_default()

        self.nodes_store = Gio.ListStore.new(NodeItem)
        self.topics_store = Gio.ListStore.new(TopicItem)
        self.services_store = Gio.ListStore.new(ServiceItem)
        self.actions_store = Gio.ListStore.new(ActionItem)
        self.interfaces_store = Gio.ListStore.new(InterfaceTypeItem)
        self.parameters_store = Gio.ListStore.new(ParameterItem)
        self.pkgs_store = Gio.ListStore.new(GObject.GObject)

        self._logger = self._make_logger()
        self.ros2_node = self._make_node()
        self.is_running = True
        self.start_time = self.ros2_node.get_clock().now()
        self._rpc_lock = Lock()
        self._dummy_lock = Lock()

        self._rng = random.Random()
        self._dummy_graph: Dict[str, Any] | None = None
        self._ensure_dummy_graph(
            nodes=self._DEFAULT_NODE_COUNT,
            topics=self._DEFAULT_TOPIC_COUNT,
            services=self._DEFAULT_SERVICE_COUNT,
            actions=self._DEFAULT_ACTION_COUNT,
            params_per_node=self._DEFAULT_PARAM_COUNT,
        )

    def _now_time(self) -> _DummyTime:
        return _DummyTime.from_seconds(time.time())

    def _make_logger(self):
        def _log(level: str, message: str) -> None:
            print(f"[{level.upper()}] {message}")

        return SimpleNamespace(
            info=lambda message: _log("info", message),
            warning=lambda message: _log("warning", message),
            error=lambda message: _log("error", message),
            fatal=lambda message: _log("fatal", message),
            debug=lambda message: _log("debug", message),
        )

    def _make_timer(self, period: float, callback: Callable):
        def _on_tick() -> bool:
            try:
                callback()
            except Exception as exc:
                print(f"Dummy timer callback error: {exc}")
            return True

        source_id = GLib.timeout_add(max(1, int(period * 1000)), _on_tick)

        def _destroy() -> None:
            nonlocal source_id
            if source_id is not None:
                GLib.source_remove(source_id)
                source_id = None

        return SimpleNamespace(destroy=_destroy, cancel=_destroy)

    def _make_publisher(self, msg_type: Any, topic_name: str):
        state = {"destroyed": False}
        pub = SimpleNamespace(msg_type=msg_type, topic_name=topic_name, last_message=None)

        def _publish(msg: Any) -> None:
            if state["destroyed"]:
                return
            pub.last_message = msg

        def _destroy() -> None:
            state["destroyed"] = True

        pub.publish = _publish
        pub.destroy = _destroy
        return pub

    def _make_subscription(self, msg_type: Any, topic_name: str, callback: Callable):
        state = {"destroyed": False}
        sub = SimpleNamespace(msg_type=msg_type, topic_name=topic_name, callback=callback)

        def _destroy() -> None:
            state["destroyed"] = True

        sub.destroy = _destroy
        return sub

    def _make_node(self):
        publishers: List[Any] = []
        subscriptions: List[Any] = []

        def _get_name() -> str:
            return self._sanitize_name(self.app.settings.get_string("gui-node-name"))

        def _get_namespace() -> str:
            return self._normalize_namespace(self.app.settings.get_string("gui-node-namespace"))

        def _get_clock():
            return SimpleNamespace(now=self._now_time)

        def _get_logger():
            return self._logger

        def _create_publisher(msg_type: Any, topic_name: str, qos_profile: Any = None):
            pub = self._make_publisher(msg_type, topic_name)
            publishers.append(pub)
            return pub

        def _destroy_publisher(pub) -> bool:
            if pub in publishers:
                publishers.remove(pub)
                if hasattr(pub, "destroy"):
                    pub.destroy()
                return True
            return False

        def _create_subscription(msg_type: Any, topic_name: str, callback: Callable, qos_profile: Any = None):
            sub = self._make_subscription(msg_type, topic_name, callback)
            subscriptions.append(sub)
            return sub

        def _destroy_subscription(sub) -> bool:
            if sub in subscriptions:
                subscriptions.remove(sub)
                if hasattr(sub, "destroy"):
                    sub.destroy()
                return True
            return False

        def _create_timer(period: float, callback: Callable):
            return self._make_timer(period, callback)

        def _destroy_node() -> None:
            for pub in list(publishers):
                _destroy_publisher(pub)
            for sub in list(subscriptions):
                _destroy_subscription(sub)

        node = SimpleNamespace(
            publishers=publishers,
            subscriptions=subscriptions,
            get_name=_get_name,
            get_namespace=_get_namespace,
            get_clock=_get_clock,
            get_logger=_get_logger,
            create_publisher=_create_publisher,
            destroy_publisher=_destroy_publisher,
            create_subscription=_create_subscription,
            destroy_subscription=_destroy_subscription,
            create_timer=_create_timer,
            destroy_node=_destroy_node,
        )
        return node

    def _ensure_spin_thread(self):
        """No-op for the dummy connector."""
        return

    def _set_running_action_state(self, running: bool):
        try:
            self.app.lookup_action("ros2-node-is-running").set_state(GLib.Variant.new_boolean(running))
        except Exception:
            pass

    def start_node(self, *args, **kwargs):
        self.start_time = self.ros2_node.get_clock().now()
        self.is_running = True
        self._set_running_action_state(True)
        self._ensure_dummy_graph(
            nodes=self._DEFAULT_NODE_COUNT,
            topics=self._DEFAULT_TOPIC_COUNT,
            services=self._DEFAULT_SERVICE_COUNT,
            actions=self._DEFAULT_ACTION_COUNT,
            params_per_node=self._DEFAULT_PARAM_COUNT,
        )

    def stop_node(self, *args, **kwargs):
        self.is_running = False
        self._set_running_action_state(False)

    def restart_node(self, *args, **kwargs):
        """Restart the dummy node."""
        if self.is_running:
            self.stop_node()
        self.start_node()

    def spin(self, *args, **kwargs):
        return False

    def shutdown(self):
        self.stop_node()

    def on_node_state_changed(self, action: Gio.Action, value: GLib.Variant):
        action.set_state(GLib.Variant.new_boolean(self.is_running))

    def set_ros_domain_id(self, domain_id: int):
        # TODO implement this using app settings to seed dummy data per domain
        pass

    def add_publisher(self, msg_type: Any, topic_name: str, qos_profile: Any = 10, **kwargs) -> Any:
        return self.ros2_node.create_publisher(msg_type, topic_name, qos_profile=qos_profile)

    def destroy_publisher(self, pub: Any) -> bool:
        if pub in list(self.ros2_node.publishers):
            return self.ros2_node.destroy_publisher(pub)
        raise RuntimeError("Publisher cannot be destroyed")

    def add_timer_callback(self, period: float, callback: Callable) -> Any:
        return self.ros2_node.create_timer(period, callback)

    def add_subsciption(self, msg_type: Any, topic_name: str, callback: Callable) -> Any:
        return self.ros2_node.create_subscription(msg_type, topic_name, callback, 10)

    def destroy_subscription(self, sub: Any) -> bool:
        if sub in list(self.ros2_node.subscriptions):
            return self.ros2_node.destroy_subscription(sub)
        raise RuntimeError("Subscription cannot be destroyed")

    def call_service(
        self,
        srv_type: Any,
        srv_name: str,
        request: Any,
        timeout_sec: int = -1,
    ) -> Any:
        response = None
        try:
            response = srv_type.Response()
        except Exception:
            response = None

        if response is not None:
            self._fill_message_randomly(response)
            return response

        return None

    def send_action_goal(
        self,
        action_type: Any,
        action_name: str,
        goal: Any,
        feedback_callback: Callable | None = None,
        timeout_sec: int = -1,
    ):
        """Send a dummy action goal and return a dummy action client and goal future."""
        feedback_msg = self._build_action_feedback(action_type)
        result_msg = self._build_action_result(action_type)
        if feedback_callback and feedback_msg is not None:
            GLib.idle_add(lambda: feedback_callback(feedback_msg))

        result_future = _resolved_future(SimpleNamespace(result=result_msg))
        goal_handle = SimpleNamespace(
            accepted=True,
            get_result_async=lambda: result_future,
            cancel_goal_async=lambda: _resolved_future(True),
        )
        goal_future = _resolved_future(goal_handle)
        action_client = SimpleNamespace(action_type=action_type, action_name=action_name)
        return action_client, goal_future

    def refresh_nodes_store(self, dummy_num: int = _DEFAULT_NODE_COUNT) -> Gio.ListStore:
        """Refresh the nodes store with dummy nodes."""
        self.nodes_store.remove_all()

        self._ensure_dummy_graph(nodes=dummy_num)
        graph = self._dummy_graph
        if graph is None:
            self.emit("nodes-refreshed", self.nodes_store)
            return self.nodes_store

        try:
            node_items: List[NodeItem] = []
            node_specs = graph["nodes"][: max(0, dummy_num)]

            for spec in node_specs:
                node_item = NodeItem(
                    namespace=spec["namespace"],
                    name=spec["name"],
                    hidden=spec["hidden"],
                )
                counts = graph["node_counts"].get(spec["full_name"], {})
                node_item.publisher_count = counts.get("publishers", 0)
                node_item.subscriber_count = counts.get("subscribers", 0)
                node_item.service_server_count = counts.get("service_servers", 0)
                node_item.service_client_count = counts.get("service_clients", 0)
                node_item.action_server_count = counts.get("action_servers", 0)
                node_item.action_client_count = counts.get("action_clients", 0)
                node_items.append(node_item)

            for item in node_items:
                self.nodes_store.append(item)
            self.nodes_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))

        except Exception as exc:
            print(f"Error getting dummy nodes: {exc}")
            self.nodes_store.remove_all()

        finally:
            self.emit("nodes-refreshed", self.nodes_store)

        return self.nodes_store

    def get_available_nodes(self, dummy_num: int = _DEFAULT_NODE_COUNT) -> Gio.ListStore:
        """Compatibility wrapper; prefer refresh_nodes_store()."""
        return self.refresh_nodes_store(dummy_num=dummy_num)

    def refresh_topics_store(self, dummy_num: int = _DEFAULT_TOPIC_COUNT) -> Gio.ListStore:
        """Refresh the topics store with dummy topics."""
        self.topics_store.remove_all()

        self._ensure_dummy_graph(topics=dummy_num)
        graph = self._dummy_graph
        if graph is None:
            self.emit("topics-refreshed", self.topics_store)
            return self.topics_store

        try:
            topic_items: List[TopicItem] = []
            topics = graph["topics"][: max(0, dummy_num)]
            if not self.app.settings.get_boolean("show-action-topics"):
                topics = self._filter_action_topics([(t["full_name"], [t["type"]]) for t in topics])
                topics = [
                    {"full_name": name, "type": types[0], "hidden": self._is_hidden_name(name)}
                    for name, types in topics
                ]

            for spec in topics:
                topic_full_name = spec["full_name"]
                topic_namespace, topic_name = topic_full_name.rsplit("/", 1)
                topic_items.append(
                    TopicItem(
                        name=topic_name,
                        namespace=topic_namespace,
                        interface_full_name=spec["type"],
                        hidden=spec["hidden"],
                    )
                )

            for item in topic_items:
                self.topics_store.append(item)
            self.topics_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))

        except Exception as exc:
            print(f"Error getting dummy topics: {exc}")
            self.topics_store.remove_all()

        finally:
            self.emit("topics-refreshed", self.topics_store)

        return self.topics_store

    def get_available_topics(self, dummy_num: int = _DEFAULT_TOPIC_COUNT) -> Gio.ListStore:
        """Compatibility wrapper; prefer refresh_topics_store()."""
        return self.refresh_topics_store(dummy_num=dummy_num)

    def get_publishers_by_node(self, node: NodeItem, dummy_num: int = 20) -> Gio.ListStore:
        """Get dummy publishers for a specific node."""
        self._ensure_dummy_graph()
        graph = self._dummy_graph
        if graph is None:
            return Gio.ListStore.new(TopicItem)

        try:
            publishers = graph["node_publishers"].get(node.full_name, [])
            publisher_store = Gio.ListStore.new(TopicItem)

            for spec in publishers[: max(0, dummy_num)]:
                if not re.search("/(msg|action)/", spec["type"]):
                    continue

                topic_full_name = spec["full_name"]
                topic_namespace, topic_name = topic_full_name.rsplit("/", 1)

                is_action_topic = re.search(r"/_action/(status|feedback)", topic_full_name)
                if is_action_topic and not self.app.settings.get_boolean("show-action-topics"):
                    continue

                topic = TopicItem(
                    name=topic_name,
                    namespace=topic_namespace,
                    interface_full_name=spec["type"],
                    hidden=spec["hidden"],
                )

                publisher_store.append(topic)

            publisher_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return publisher_store

        except Exception as exc:
            print(f"Error getting dummy publishers for node '{node.full_name}': {exc}")
            return Gio.ListStore.new(TopicItem)

    def get_subscribers_by_node(self, node: NodeItem, dummy_num: int = 20) -> Gio.ListStore:
        """Get dummy subscribers for a specific node."""
        self._ensure_dummy_graph()
        graph = self._dummy_graph
        if graph is None:
            return Gio.ListStore.new(TopicItem)

        try:
            subscribers = graph["node_subscribers"].get(node.full_name, [])
            subscriber_store = Gio.ListStore.new(TopicItem)

            for spec in subscribers[: max(0, dummy_num)]:
                if not re.search("/(msg|action)/", spec["type"]):
                    continue

                topic_full_name = spec["full_name"]
                topic_namespace, topic_name = topic_full_name.rsplit("/", 1)

                is_action_topic = re.search(r"/_action/(status|feedback)", topic_full_name)
                if is_action_topic and not self.app.settings.get_boolean("show-action-topics"):
                    continue

                topic = TopicItem(
                    name=topic_name,
                    namespace=topic_namespace,
                    interface_full_name=spec["type"],
                    hidden=spec["hidden"],
                )

                subscriber_store.append(topic)

            subscriber_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return subscriber_store

        except Exception as exc:
            print(f"Error getting dummy subscribers for node '{node.full_name}': {exc}")
            return Gio.ListStore.new(TopicItem)

    def refresh_services_store(self, dummy_num: int = _DEFAULT_SERVICE_COUNT) -> Gio.ListStore:
        """Refresh the services store with dummy services."""
        self.services_store.remove_all()

        self._ensure_dummy_graph(services=dummy_num)
        graph = self._dummy_graph
        if graph is None:
            self.emit("services-refreshed", self.services_store)
            return self.services_store

        try:
            service_items: List[ServiceItem] = []
            services = graph["services"][: max(0, dummy_num)]
            if not self.app.settings.get_boolean("show-action-services"):
                services = self._filter_action_services([(s["full_name"], [s["type"]]) for s in services])
                services = [
                    {"full_name": name, "type": types[0], "hidden": self._is_hidden_name(name)}
                    for name, types in services
                ]
            if not self.app.settings.get_boolean("show-parameter-services"):
                services = self._filter_param_services([(s["full_name"], [s["type"]]) for s in services])
                services = [
                    {"full_name": name, "type": types[0], "hidden": self._is_hidden_name(name)}
                    for name, types in services
                ]

            for spec in services:
                service_full_name = spec["full_name"]
                service_namespace, service_name = service_full_name.rsplit("/", 1)
                if not re.search("/srv/", spec["type"]):
                    continue

                service_items.append(
                    ServiceItem(
                        name=service_name,
                        namespace=service_namespace,
                        interface_full_name=spec["type"],
                        hidden=spec["hidden"],
                    )
                )

            for item in service_items:
                self.services_store.append(item)
            self.services_store.sort(
                compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name)
            )

        except Exception as exc:
            print(f"Error getting dummy services: {exc}")
            self.services_store.remove_all()

        finally:
            self.emit("services-refreshed", self.services_store)

        return self.services_store

    def get_available_services(self, dummy_num: int = _DEFAULT_SERVICE_COUNT) -> Gio.ListStore:
        """Compatibility wrapper; prefer refresh_services_store()."""
        return self.refresh_services_store(dummy_num=dummy_num)

    def get_service_clients_by_node(self, node: NodeItem, dummy_num: int = 20) -> Gio.ListStore:
        """Get dummy service clients for a specific node."""
        self._ensure_dummy_graph()
        graph = self._dummy_graph
        if graph is None:
            return Gio.ListStore.new(ServiceItem)

        try:
            service_clients = graph["node_service_clients"].get(node.full_name, [])
            client_store = Gio.ListStore.new(ServiceItem)

            for spec in service_clients[: max(0, dummy_num)]:
                if not re.search("/srv/", spec["type"]):
                    continue

                service_full_name = spec["full_name"]
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
                    interface_full_name=spec["type"],
                    hidden=spec["hidden"],
                )

                client_store.append(service)

            client_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return client_store

        except Exception as exc:
            print(f"Error getting dummy service clients for node '{node.full_name}': {exc}")
            return Gio.ListStore.new(ServiceItem)

    def get_service_servers_by_node(self, node: NodeItem, dummy_num: int = 20) -> Gio.ListStore:
        """Get dummy service servers for a specific node."""
        self._ensure_dummy_graph()
        graph = self._dummy_graph
        if graph is None:
            return Gio.ListStore.new(ServiceItem)

        try:
            service_servers = graph["node_service_servers"].get(node.full_name, [])
            server_store = Gio.ListStore.new(ServiceItem)

            for spec in service_servers[: max(0, dummy_num)]:
                if not re.search("/srv/", spec["type"]):
                    continue

                service_full_name = spec["full_name"]
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
                    interface_full_name=spec["type"],
                    hidden=spec["hidden"],
                )

                server_store.append(service)

            server_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return server_store

        except Exception as exc:
            print(f"Error getting dummy service servers for node '{node.full_name}': {exc}")
            return Gio.ListStore.new(ServiceItem)

    def refresh_actions_store(self, dummy_num: int = _DEFAULT_ACTION_COUNT) -> Gio.ListStore:
        """Refresh the actions store with dummy actions."""
        self.actions_store.remove_all()

        self._ensure_dummy_graph(actions=dummy_num)
        graph = self._dummy_graph
        if graph is None:
            self.emit("actions-refreshed", self.actions_store)
            return self.actions_store

        try:
            action_items: List[ActionItem] = []
            available_actions = graph["actions"][: max(0, dummy_num)]

            for spec in available_actions:
                action_full_name = spec["full_name"]
                action_namespace, action_name = action_full_name.rsplit("/", 1)
                action_items.append(
                    ActionItem(
                        name=action_name,
                        namespace=action_namespace,
                        interface_full_name=spec["type"],
                        hidden=spec["hidden"],
                    )
                )

            for item in action_items:
                self.actions_store.append(item)
            self.actions_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))

        except Exception as exc:
            print(f"Error getting dummy actions: {exc}")
            self.actions_store.remove_all()

        finally:
            self.emit("actions-refreshed", self.actions_store)

        return self.actions_store

    def get_available_actions(self, dummy_num: int = _DEFAULT_ACTION_COUNT) -> Gio.ListStore:
        """Compatibility wrapper; prefer refresh_actions_store()."""
        return self.refresh_actions_store(dummy_num=dummy_num)

    def get_action_clients_by_node(self, node: NodeItem, dummy_num: int = 10) -> Gio.ListStore:
        """Get dummy action clients for a specific node."""
        self._ensure_dummy_graph()
        graph = self._dummy_graph
        if graph is None:
            return Gio.ListStore.new(ActionItem)

        try:
            action_clients = graph["node_action_clients"].get(node.full_name, [])
            client_store = Gio.ListStore.new(ActionItem)

            for spec in action_clients[: max(0, dummy_num)]:
                if not re.search("/action/", spec["type"]):
                    continue

                action_full_name = spec["full_name"]
                action_namespace, action_name = action_full_name.rsplit("/", 1)
                action = ActionItem(
                    name=action_name,
                    namespace=action_namespace,
                    interface_full_name=spec["type"],
                    hidden=spec["hidden"],
                )

                client_store.append(action)

            client_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return client_store

        except Exception as exc:
            print(f"Error getting dummy action clients for node '{node.full_name}': {exc}")
            return Gio.ListStore.new(ActionItem)

    def get_action_servers_by_node(self, node: NodeItem, dummy_num: int = 10) -> Gio.ListStore:
        """Get dummy action servers for a specific node."""
        self._ensure_dummy_graph()
        graph = self._dummy_graph
        if graph is None:
            return Gio.ListStore.new(ActionItem)

        try:
            action_servers = graph["node_action_servers"].get(node.full_name, [])
            server_store = Gio.ListStore.new(ActionItem)

            for spec in action_servers[: max(0, dummy_num)]:
                if not re.search("/action/", spec["type"]):
                    continue

                action_full_name = spec["full_name"]
                action_namespace, action_name = action_full_name.rsplit("/", 1)
                action = ActionItem(
                    name=action_name,
                    namespace=action_namespace,
                    interface_full_name=spec["type"],
                    hidden=spec["hidden"],
                )

                server_store.append(action)

            server_store.sort(compare_func=lambda a, b: (a.full_name > b.full_name) - (a.full_name < b.full_name))
            return server_store

        except Exception as exc:
            print(f"Error getting dummy action servers for node '{node.full_name}': {exc}")
            return Gio.ListStore.new(ActionItem)

    def refresh_parameters_store(self, node: NodeItem, dummy_num: int = _DEFAULT_PARAM_COUNT) -> Gio.ListStore:
        """Refresh the parameters store for a specific node with dummy parameters."""
        self.parameters_store.remove_all()

        self._ensure_dummy_graph(params_per_node=dummy_num)
        graph = self._dummy_graph
        if graph is None:
            self.emit("parameters-refreshed", self.parameters_store)
            return self.parameters_store

        try:
            parameters: List[ParameterItem] = []
            param_specs = graph["node_parameters"].get(node.full_name, [])[: max(0, dummy_num)]

            for spec in param_specs:
                param = ParameterItem(name=spec["name"], node=node)
                param.type = spec.get("type")
                param.type_str = spec.get("type_str", "")
                param.read_only = spec.get("read_only", False)
                param.description = spec.get("description", "")
                param.dynamic_typing = spec.get("dynamic_typing", False)
                param.integer_range = spec.get("integer_range")
                param.floating_point_range = spec.get("floating_point_range")
                param.additional_constraints = spec.get("additional_constraints")
                param.value = spec.get("value")
                parameters.append(param)

            for item in parameters:
                self.parameters_store.append(item)
            self.parameters_store.sort(compare_func=lambda a, b: (a.name > b.name) - (a.name < b.name))

        except Exception as exc:
            print(f"Error getting dummy parameters for node '{node.full_name}': {exc}")
            self.parameters_store.remove_all()

        finally:
            self.emit("parameters-refreshed", self.parameters_store)

        return self.parameters_store

    def get_parameters_by_node(self, node: NodeItem, dummy_num: int = _DEFAULT_PARAM_COUNT) -> Gio.ListStore:
        """Compatibility wrapper; prefer refresh_parameters_store()."""
        return self.refresh_parameters_store(node=node, dummy_num=dummy_num)

    def get_parameter_value(self, parameter: ParameterItem) -> object | None:
        """Get dummy parameter value for a specific parameter."""
        if parameter.value is not None:
            return parameter.value

        self._ensure_dummy_graph()
        graph = self._dummy_graph
        if graph is None:
            return None

        node_params = graph["node_parameters"].get(parameter.node.full_name, [])
        for spec in node_params:
            if spec["name"] == parameter.name:
                return spec.get("value")

        return None

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
        self.refresh_nodes_store()
        self.refresh_topics_store()
        self.refresh_services_store()
        self.refresh_actions_store()

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with the specified severity level (debug, [info], warning, error, fatal)."""
        logger = self._logger
        if level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        elif level == "fatal":
            logger.fatal(message)
        elif level == "debug":
            logger.debug(message)
        else:
            logger.info(f"{level} is not a valid logging level. Defaulting to info.")
            logger.info(message)

    # Dummy graph helpers
    def _ensure_dummy_graph(
        self,
        nodes: int | None = None,
        topics: int | None = None,
        services: int | None = None,
        actions: int | None = None,
        params_per_node: int | None = None,
    ) -> None:
        with self._dummy_lock:
            if self._dummy_graph is None:
                self._build_dummy_graph(
                    nodes=nodes or self._DEFAULT_NODE_COUNT,
                    topics=topics or self._DEFAULT_TOPIC_COUNT,
                    services=services or self._DEFAULT_SERVICE_COUNT,
                    actions=actions or self._DEFAULT_ACTION_COUNT,
                    params_per_node=params_per_node or self._DEFAULT_PARAM_COUNT,
                )
                return

            sizes = self._dummy_graph["sizes"]
            needs_rebuild = False

            if nodes and nodes > sizes["nodes"]:
                needs_rebuild = True
            if topics and topics > sizes["topics"]:
                needs_rebuild = True
            if services and services > sizes["services"]:
                needs_rebuild = True
            if actions and actions > sizes["actions"]:
                needs_rebuild = True
            if params_per_node and params_per_node > sizes["params_per_node"]:
                needs_rebuild = True

            gui_node_full_name = self._make_full_name(
                self.app.settings.get_string("gui-node-namespace"),
                self._sanitize_name(self.app.settings.get_string("gui-node-name")),
            )
            if gui_node_full_name != sizes.get("gui_node_full_name"):
                needs_rebuild = True

            if needs_rebuild:
                self._build_dummy_graph(
                    nodes=max(nodes or 0, sizes["nodes"]),
                    topics=max(topics or 0, sizes["topics"]),
                    services=max(services or 0, sizes["services"]),
                    actions=max(actions or 0, sizes["actions"]),
                    params_per_node=max(params_per_node or 0, sizes["params_per_node"]),
                )

    def _build_dummy_graph(
        self,
        nodes: int,
        topics: int,
        services: int,
        actions: int,
        params_per_node: int,
    ) -> None:
        namespaces = self._build_namespace_pool(target=max(12, nodes))
        gui_node_full_name = self._make_full_name(
            self.app.settings.get_string("gui-node-namespace"),
            self._sanitize_name(self.app.settings.get_string("gui-node-name")),
        )

        node_specs: List[Dict[str, Any]] = []
        used_nodes = set()

        gui_name = self._sanitize_name(self.app.settings.get_string("gui-node-name"))
        gui_ns = self._normalize_namespace(self.app.settings.get_string("gui-node-namespace"))
        gui_full = self._make_full_name(gui_ns, gui_name)
        node_specs.append(
            {
                "name": gui_name,
                "namespace": gui_ns if gui_ns != "/" else "",
                "full_name": gui_full,
                "hidden": self._is_hidden_name(gui_full),
            }
        )
        used_nodes.add(gui_full)

        while len(node_specs) < nodes:
            base_name = self._rng.choice(self._NODE_NAME_POOL)
            name = self._unique_name(base_name, used_nodes, namespaces)
            namespace = self._rng.choice(namespaces)
            name, hidden = self._maybe_hidden(name)
            full_name = self._make_full_name(namespace, name)
            if full_name in used_nodes:
                continue
            node_specs.append(
                {
                    "name": name,
                    "namespace": namespace if namespace != "/" else "",
                    "full_name": full_name,
                    "hidden": hidden,
                }
            )
            used_nodes.add(full_name)

        action_specs = self._build_action_specs(actions, namespaces)

        topic_specs = self._build_topic_specs(topics, namespaces, action_specs)
        service_specs = self._build_service_specs(services, namespaces, node_specs, action_specs)

        node_keys = [spec["full_name"] for spec in node_specs]

        node_publishers = self._assign_to_nodes(node_keys, topic_specs, min_count=1, max_count=3)
        node_subscribers = self._assign_to_nodes(node_keys, topic_specs, min_count=0, max_count=4)
        node_service_servers = self._assign_to_nodes(node_keys, service_specs, min_count=1, max_count=1)
        node_service_clients = self._assign_to_nodes(node_keys, service_specs, min_count=0, max_count=3)
        node_action_servers = self._assign_to_nodes(node_keys, action_specs, min_count=1, max_count=1)
        node_action_clients = self._assign_to_nodes(node_keys, action_specs, min_count=0, max_count=3)

        node_counts = {}
        for key in node_keys:
            node_counts[key] = {
                "publishers": len(node_publishers.get(key, [])),
                "subscribers": len(node_subscribers.get(key, [])),
                "service_servers": len(node_service_servers.get(key, [])),
                "service_clients": len(node_service_clients.get(key, [])),
                "action_servers": len(node_action_servers.get(key, [])),
                "action_clients": len(node_action_clients.get(key, [])),
            }

        node_parameters = self._build_parameter_specs(node_specs, params_per_node)

        self._dummy_graph = {
            "sizes": {
                "nodes": len(node_specs),
                "topics": len(topic_specs),
                "services": len(service_specs),
                "actions": len(action_specs),
                "params_per_node": params_per_node,
                "gui_node_full_name": gui_node_full_name,
            },
            "nodes": node_specs,
            "topics": topic_specs,
            "services": service_specs,
            "actions": action_specs,
            "node_publishers": node_publishers,
            "node_subscribers": node_subscribers,
            "node_service_servers": node_service_servers,
            "node_service_clients": node_service_clients,
            "node_action_servers": node_action_servers,
            "node_action_clients": node_action_clients,
            "node_counts": node_counts,
            "node_parameters": node_parameters,
        }

    def _build_namespace_pool(self, target: int) -> List[str]:
        namespaces = set(self._NAMESPACE_ROOTS)
        while len(namespaces) < target:
            root = self._rng.choice(list(namespaces))
            suffix = self._rng.choice(self._NAMESPACE_SUFFIXES)
            if root == "/":
                namespaces.add(f"/{suffix}")
            else:
                namespaces.add(f"{root.rstrip('/')}/{suffix}")
        return sorted(namespaces)

    def _build_topic_specs(
        self,
        target: int,
        namespaces: List[str],
        action_specs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        topic_specs: List[Dict[str, Any]] = []
        used = set()

        def add_topic(full_name: str, type_full_name: str) -> None:
            if full_name in used:
                return
            topic_specs.append(
                {
                    "full_name": full_name,
                    "type": type_full_name,
                    "hidden": self._is_hidden_name(full_name),
                }
            )
            used.add(full_name)

        topic_pool = list(self._TOPIC_POOL)
        for base_name, type_name in topic_pool:
            namespace = self._rng.choice(namespaces)
            full_name = self._make_full_name(namespace, base_name)
            add_topic(full_name, type_name)

        for action in action_specs:
            for topic_name, topic_type in self._build_action_topics(action["full_name"], action["type"]):
                add_topic(topic_name, topic_type)

        while len(topic_specs) < target and topic_pool:
            base_name, type_name = self._rng.choice(topic_pool)
            namespace = self._rng.choice(namespaces)
            name = base_name
            if self._rng.random() < 0.2:
                name = f"{name}_{self._rng.randint(1, 99)}"
            name, _ = self._maybe_hidden(name)
            full_name = self._make_full_name(namespace, name)
            add_topic(full_name, type_name)

        return topic_specs

    def _build_service_specs(
        self,
        target: int,
        namespaces: List[str],
        node_specs: List[Dict[str, Any]],
        action_specs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        service_specs: List[Dict[str, Any]] = []
        used = set()

        def add_service(full_name: str, type_full_name: str) -> None:
            if full_name in used:
                return
            service_specs.append(
                {
                    "full_name": full_name,
                    "type": type_full_name,
                    "hidden": self._is_hidden_name(full_name),
                }
            )
            used.add(full_name)

        param_suffixes = [
            "describe_parameters",
            "get_parameters",
            "get_parameter_types",
            "list_parameters",
            "set_parameters",
            "set_parameters_atomically",
            "get_type_description",
        ]

        for node in self._rng.sample(node_specs, k=min(len(node_specs), max(1, len(node_specs) // 4))):
            for suffix in param_suffixes:
                full_name = self._join_full(node["full_name"], suffix)
                add_service(full_name, "rcl_interfaces/srv/GetParameters")

        for action in action_specs:
            for service_name, service_type in self._build_action_services(action["full_name"], action["type"]):
                add_service(service_name, service_type)

        service_pool = list(self._SERVICE_POOL)
        for base_name, type_name in service_pool:
            namespace = self._rng.choice(namespaces)
            full_name = self._make_full_name(namespace, base_name)
            add_service(full_name, type_name)

        while len(service_specs) < target and service_pool:
            base_name, type_name = self._rng.choice(service_pool)
            namespace = self._rng.choice(namespaces)
            name = base_name
            if self._rng.random() < 0.2:
                name = f"{name}_{self._rng.randint(1, 99)}"
            name, _ = self._maybe_hidden(name)
            full_name = self._make_full_name(namespace, name)
            add_service(full_name, type_name)

        return service_specs

    def _build_action_specs(self, target: int, namespaces: List[str]) -> List[Dict[str, Any]]:
        action_specs: List[Dict[str, Any]] = []
        used = set()

        action_pool = list(self._ACTION_POOL)
        if not action_pool:
            return action_specs

        while len(action_specs) < target:
            base_name, type_name = self._rng.choice(action_pool)
            namespace = self._rng.choice(namespaces)
            name = base_name
            if self._rng.random() < 0.2:
                name = f"{name}_{self._rng.randint(1, 9)}"
            name, hidden = self._maybe_hidden(name)
            full_name = self._make_full_name(namespace, name)
            if full_name in used:
                continue
            action_specs.append(
                {
                    "full_name": full_name,
                    "type": type_name,
                    "hidden": hidden,
                }
            )
            used.add(full_name)

        return action_specs

    def _build_parameter_specs(
        self, node_specs: List[Dict[str, Any]], per_node: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        node_parameters: Dict[str, List[Dict[str, Any]]] = {}

        for node in node_specs:
            params: List[Dict[str, Any]] = []
            used_names = set()
            while len(params) < per_node:
                base_name, type_str = self._rng.choice(self._PARAM_POOL)
                name = base_name
                if self._rng.random() < 0.2:
                    name = f"{name}_{self._rng.randint(1, 9)}"
                if name in used_names:
                    continue
                used_names.add(name)
                value = self._random_param_value(name, type_str)
                params.append(
                    {
                        "name": name,
                        "type": self._PARAM_TYPE_CODES.get(type_str, 0),
                        "type_str": type_str,
                        "value": value,
                        "read_only": self._rng.random() < 0.1,
                        "dynamic_typing": self._rng.random() < 0.05,
                        "description": f"Dummy parameter '{name}'",
                        "integer_range": None,
                        "floating_point_range": None,
                        "additional_constraints": None,
                    }
                )

            node_parameters[node["full_name"]] = params

        return node_parameters

    def _build_action_topics(self, action_full_name: str, action_type: str) -> List[Tuple[str, str]]:
        return [
            (self._join_full(action_full_name, "_action/feedback"), "std_msgs/msg/String"),
            (self._join_full(action_full_name, "_action/status"), "action_msgs/msg/GoalStatusArray"),
        ]

    def _build_action_services(self, action_full_name: str, action_type: str) -> List[Tuple[str, str]]:
        return [
            (self._join_full(action_full_name, "_action/send_goal"), "std_srvs/srv/Trigger"),
            (self._join_full(action_full_name, "_action/get_result"), "std_srvs/srv/Trigger"),
            (self._join_full(action_full_name, "_action/cancel_goal"), "action_msgs/srv/CancelGoal"),
        ]

    def _assign_to_nodes(
        self,
        node_keys: List[str],
        entries: List[Dict[str, Any]],
        min_count: int,
        max_count: int,
    ) -> Dict[str, List[Dict[str, Any]]]:
        mapping = {key: [] for key in node_keys}
        if not node_keys:
            return mapping

        for entry in entries:
            count = self._rng.randint(min_count, max_count)
            count = min(count, len(node_keys))
            chosen = self._rng.sample(node_keys, k=count) if count > 0 else []
            for key in chosen:
                mapping[key].append(entry)
        return mapping

    def _make_full_name(self, namespace: str, name: str) -> str:
        namespace = self._normalize_namespace(namespace)
        if namespace == "/":
            return f"/{name}"
        return f"{namespace}/{name}"

    def _join_full(self, prefix: str, name: str) -> str:
        if prefix.endswith("/"):
            return f"{prefix}{name}"
        return f"{prefix}/{name}"

    def _normalize_namespace(self, namespace: str) -> str:
        if not namespace or namespace == "/":
            return "/"
        namespace = namespace.strip()
        if not namespace.startswith("/"):
            namespace = f"/{namespace}"
        return namespace.rstrip("/")

    def _sanitize_name(self, name: str) -> str:
        name = name.strip()
        if name.startswith("/"):
            name = name[1:]
        return name or "insight_gui"

    def _is_hidden_name(self, full_name: str) -> bool:
        parts = [p for p in full_name.split("/") if p]
        return any(part.startswith("_") for part in parts)

    def _maybe_hidden(self, name: str) -> Tuple[str, bool]:
        if name.startswith("_"):
            return name, True
        if self._rng.random() < 0.05:
            return f"_{name}", True
        return name, False

    def _unique_name(self, base_name: str, used_full_names: set, namespaces: List[str]) -> str:
        name = base_name
        suffix = 1
        while True:
            candidate = name
            namespace = self._rng.choice(namespaces)
            full_name = self._make_full_name(namespace, candidate)
            if full_name not in used_full_names:
                return candidate
            suffix += 1
            name = f"{base_name}_{suffix}"

    def _random_param_value(self, name: str, type_str: str) -> Any:
        if "frame" in name:
            return self._rng.choice(["map", "odom", "base_link", "base_footprint", "camera_link"])
        if "topic" in name:
            return self._rng.choice(["/cmd_vel", "/scan", "/tf", "/tf_static"])

        if type_str == "bool":
            return self._rng.choice([True, False])
        if type_str == "integer":
            return self._rng.randint(0, 100)
        if type_str == "double":
            return round(self._rng.uniform(0.0, 10.0), 3)
        if type_str == "string":
            return self._rng.choice(["default", "auto", "enabled", "disabled", "nav2", "slam"])
        if type_str == "byte_array":
            return [self._rng.randint(0, 255) for _ in range(self._rng.randint(3, 8))]
        if type_str == "bool_array":
            return [self._rng.choice([True, False]) for _ in range(self._rng.randint(2, 5))]
        if type_str == "integer_array":
            return [self._rng.randint(-10, 10) for _ in range(self._rng.randint(2, 6))]
        if type_str == "double_array":
            return [round(self._rng.uniform(-1.0, 1.0), 3) for _ in range(self._rng.randint(2, 6))]
        if type_str == "string_array":
            return [self._rng.choice(["left", "right", "front", "rear"]) for _ in range(self._rng.randint(2, 4))]

        return None

    def _fill_message_randomly(self, msg: Any, depth: int = 0) -> None:
        if msg is None or depth > 4:
            return
        if not hasattr(msg, "get_fields_and_field_types") or not hasattr(msg, "SLOT_TYPES"):
            return

        try:
            fields = msg.get_fields_and_field_types()
        except Exception:
            return

        for field_name, field_type in fields.items():
            try:
                current_value = getattr(msg, field_name)
            except Exception:
                continue

            if hasattr(current_value, "get_fields_and_field_types"):
                self._fill_message_randomly(current_value, depth=depth + 1)
                continue

            if isinstance(current_value, (list, tuple)):
                continue

            value = None
            if field_type in ("bool",):
                value = self._rng.choice([True, False])
            elif field_type.startswith("int") or field_type.startswith("uint"):
                value = self._rng.randint(0, 100)
            elif field_type.startswith("float") or field_type in ("double", "float"):
                value = round(self._rng.uniform(-10.0, 10.0), 4)
            elif field_type in ("string", "wstring"):
                value = self._rng.choice(["dummy", "example", "ros2", "insight"])
            elif field_type.endswith("Time") and hasattr(current_value, "sec"):
                try:
                    current_value.sec = int(time.time())
                    current_value.nanosec = self._rng.randint(0, int(1e9))
                except Exception:
                    pass
                continue

            if value is not None:
                try:
                    setattr(msg, field_name, value)
                except Exception:
                    continue

    def _build_action_feedback(self, action_type: Any) -> Any:
        feedback = None
        try:
            feedback = action_type.Feedback()
            self._fill_message_randomly(feedback)
        except Exception:
            feedback = None
        return SimpleNamespace(feedback=feedback)

    def _build_action_result(self, action_type: Any) -> Any:
        result = None
        try:
            result = action_type.Result()
            self._fill_message_randomly(result)
        except Exception:
            result = None
        return result
