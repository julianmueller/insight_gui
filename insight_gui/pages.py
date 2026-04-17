# =============================================================================
# pages.py
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

from __future__ import annotations
from importlib import import_module
import re

from gi.repository import GObject


class Page(GObject.Object):
    def __init__(
        self,
        *,
        title: str,
        subtitle: str,
        icon_name: str,
        page_id: str,
        group_id: str = "",
        nav_page_class,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._title = title
        self._subtitle = subtitle
        self._icon_name = icon_name
        self._page_id = page_id
        self._group_id = group_id
        if isinstance(nav_page_class, str):
            self._nav_page_class_path = nav_page_class
            self._nav_page_class = None
        else:
            self._nav_page_class = nav_page_class
            self._nav_page_class_path = f"{nav_page_class.__module__}.{nav_page_class.__name__}"

    @GObject.Property(type=str)
    def title(self) -> str:
        return self._title

    @GObject.Property(type=str)
    def subtitle(self) -> str:
        return self._subtitle

    @GObject.Property(type=str)
    def icon_name(self) -> str:
        return self._icon_name

    @GObject.Property(type=str)
    def page_id(self) -> str:
        return self._page_id

    @GObject.Property(type=str, default="")
    def group_id(self) -> str:
        return self._group_id

    @group_id.setter
    def group_id(self, group_id: str):
        self._group_id = group_id

    @GObject.Property(type=object)
    def nav_page_class(self):
        if self._nav_page_class is None:
            module_name, class_name = self._nav_page_class_path.rsplit(".", 1)
            module = import_module(module_name)
            self._nav_page_class = getattr(module, class_name)
        return self._nav_page_class

    def create_nav_page(self, **kwargs):
        return self.nav_page_class(**kwargs)

    def __eq__(self, other):
        return (
            self.title.lower() == other.title.lower()
            or self.subtitle.lower() == other.subtitle.lower()
            or self.page_id.lower() == other.page_id.lower()
        )


class PageGroup(GObject.Object):
    def __init__(
        self,
        *,
        title: str,
        subtitle: str = "",
        group_id: str = "",
        pages: list,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._title = title
        self._subtitle = subtitle
        self._group_id = group_id
        self._pages = pages

    @GObject.Property(type=int)
    def num_pages(self) -> int:
        return len(self._pages)

    @GObject.Property(type=str)
    def title(self) -> str:
        return self._title

    @GObject.Property(type=str)
    def subtitle(self) -> str:
        return self._subtitle

    @GObject.Property(type=str)
    def group_id(self) -> str:
        return self._group_id

    @GObject.Property(type=object)
    def pages(self) -> list:
        return self._pages

    def add_page(self, page: Page) -> Page:
        self._pages.append(page)
        return page

    def get_page(self, page_title: str) -> Page:
        for p in self._pages:
            if re.search(page_title, p.title, re.IGNORECASE):
                return p
        else:
            return None


def get_all_page_ids() -> list[str]:
    page_ids = []

    for group in all_pages:
        for page in group.pages:
            page_ids.append(page.page_id)
    return page_ids


# Compute and cache all pages at import time so creation only happens once.
all_pages = [
    PageGroup(
        title="Packages",
        pages=[
            Page(
                title="Packages",
                subtitle="Browse all packages",
                icon_name="package-symbolic",
                page_id="pkg_list",
                nav_page_class="insight_gui.ros2_pages.pkg_list_page.PackageListPage",
            ),
        ],
    ),
    PageGroup(
        title="Nodes",
        pages=[
            Page(
                title="Node List",
                subtitle="Browse all active nodes",
                icon_name="token-symbolic",
                page_id="node_list",
                nav_page_class="insight_gui.ros2_pages.node_list_page.NodeListPage",
            ),
            Page(
                title="Launch Files",
                subtitle="Browse launch files",
                icon_name="rocket-launch-symbolic",
                page_id="launch_list",
                nav_page_class="insight_gui.ros2_pages.launch_list_page.LaunchListPage",
            ),
            Page(
                title="Parameters",
                subtitle="Manage node parameters",
                icon_name="instant-mix-symbolic",
                page_id="param_list",
                nav_page_class="insight_gui.ros2_pages.param_list_page.ParameterListPage",
            ),
            Page(
                title="Graph",
                subtitle="ROS2 computational graph",
                icon_name="graph3-symbolic",
                page_id="graph_page",
                nav_page_class="insight_gui.ros2_pages.graph_page.GraphPage",
            ),
        ],
    ),
    PageGroup(
        title="Topics",
        pages=[
            Page(
                title="Topic List",
                subtitle="Browse topics",
                icon_name="list-t-symbolic",
                page_id="topic_list",
                nav_page_class="insight_gui.ros2_pages.topic_list_page.TopicListPage",
            ),
            Page(
                title="Publisher",
                subtitle="Publish to topics",
                icon_name="rss-feed-symbolic",
                page_id="topic_pub",
                nav_page_class="insight_gui.ros2_pages.topic_pub_page.TopicPublisherPage",
            ),
            Page(
                title="Subscriber",
                subtitle="Subscribe to topics",
                icon_name="subscriptions-symbolic",
                page_id="topic_sub",
                nav_page_class="insight_gui.ros2_pages.topic_sub_page.TopicSubscriberPage",
            ),
            Page(
                title="Image Viewer",
                subtitle="View image topics",
                icon_name="image-x-generic-symbolic",
                page_id="img_viewer",
                nav_page_class="insight_gui.ros2_pages.img_viewer_page.ImageViewerPage",
            ),
            Page(
                title="Remap",
                subtitle="Remap topics",
                icon_name="tactic-symbolic",
                page_id="remap",
                nav_page_class="insight_gui.ros2_pages.topic_remap_page.TopicRemapPage",
            ),
        ],
    ),
    PageGroup(
        title="Services",
        pages=[
            Page(
                title="Service List",
                subtitle="Browse services",
                icon_name="list-s-symbolic",
                page_id="service_list",
                nav_page_class="insight_gui.ros2_pages.service_list_page.ServiceListPage",
            ),
            Page(
                title="Service Caller",
                subtitle="Call services",
                icon_name="call-start-symbolic",
                page_id="srv_caller",
                nav_page_class="insight_gui.ros2_pages.service_call_page.ServiceCallPage",
            ),
        ],
    ),
    PageGroup(
        title="Actions",
        pages=[
            Page(
                title="Action List",
                subtitle="Browse actions",
                icon_name="list-a-symbolic",
                page_id="action_list",
                nav_page_class="insight_gui.ros2_pages.action_list_page.ActionListPage",
            ),
            Page(
                title="Action Goal",
                subtitle="Send action goals",
                icon_name="emoji-flags-symbolic",
                page_id="action_goal",
                nav_page_class="insight_gui.ros2_pages.action_goal_page.ActionGoalPage",
            ),
        ],
    ),
    PageGroup(
        title="Interfaces",
        pages=[
            Page(
                title="Interfaces",
                subtitle="Browse interface definitions",
                icon_name="shapes-symbolic",
                page_id="interface_browser",
                nav_page_class="insight_gui.ros2_pages.interface_browser_page.InterfaceBrowserPage",
            ),
        ],
    ),
    PageGroup(
        title="Transforms",
        pages=[
            Page(
                title="Transforms",
                subtitle="Inspect transformations",
                icon_name="coordinates-symbolic",
                page_id="tf",
                nav_page_class="insight_gui.ros2_pages.tf_page.TransformsPage",
            ),
            Page(
                title="Static Transform Broadcaster",
                subtitle="Broadcast to /tf_static",
                icon_name="bigtop-updates-symbolic",
                page_id="tf_static_broadcaster",
                nav_page_class="insight_gui.ros2_pages.tf_static_broadcaster_page.StaticTransformBroadcasterPage",
            ),
            Page(
                title="TF-Tree",
                subtitle="Inspect all TFs as a tree",
                icon_name="forest-symbolic",
                page_id="tf_tree",
                nav_page_class="insight_gui.ros2_pages.tf_tree_page.TFTreePage",
            ),
        ],
    ),
    PageGroup(
        title="Control",
        pages=[
            # TODO this was purely-vibe coded, so rework
            # Page(
            #     title="Controllers",
            #     subtitle="Manage ros2_control controllers",
            #     icon_name="memory-symbolic",
            #     page_id="controllers",
            #     nav_page_class=ControllerManagerPage,
            # ),
            Page(
                title="Joint States",
                subtitle="Manipulate joints",
                icon_name="sliders-horizontal-symbolic",
                page_id="joint_states",
                nav_page_class="insight_gui.ros2_pages.joint_states_page.JointStatesPage",
            ),
            Page(
                title="Teleoperator",
                subtitle="Teleoperate a robot",
                icon_name="gamepad-symbolic",
                page_id="teleop",
                nav_page_class="insight_gui.ros2_pages.teleop_page.TeleoperatorPage",
            ),
        ],
    ),
    # PageGroup(
    #     title="ROS Bags",
    #     pages=[
    #         Page(
    #             title="Recorder",
    #             subtitle="Record a ros2 bag",
    #             icon_name="money-bag-symbolic",
    #             page_id="bag_recorder",
    #             nav_page_class=BagRecorderPage,
    #         ),
    #         Page(
    #             title="Playback",
    #             subtitle="Play a ros2 bag",
    #             icon_name="money-bag-symbolic",
    #             page_id="bag_player",
    #             nav_page_class=BagPlayerPage,
    #         )
    #     ],
    # ),
    PageGroup(
        title="Diagnostics",
        pages=[
            Page(
                title="Logger",
                subtitle="System logs",
                icon_name="logviewer-symbolic",
                page_id="logger",
                nav_page_class="insight_gui.ros2_pages.log_page.LoggerPage",
            ),
            # Page(
            #     title="Documentation",
            #     subtitle="Look at the ros2 docs",
            #     icon_name="docs-symbolic",
            #     page_id="docs",
            #     nav_page_class=DocumentationPage,
            # ),
            # Page(
            #     title="Quality of Service",
            #     subtitle="Inspect QoS statistics",
            #     icon_name="editor-choice-symbolic",
            #     page_id="qos",
            #     nav_page_class=QualityOfServicePage,
            # ),
            Page(
                title="Multicast",
                subtitle="Test multicast send/receive",
                icon_name="cell-tower-symbolic",
                page_id="multicast",
                nav_page_class="insight_gui.ros2_pages.multicast_page.MulticastPage",
            ),
            Page(
                title="Doctor",
                subtitle="System diagnostics",
                icon_name="doctor-symbolic",
                page_id="doctor",
                nav_page_class="insight_gui.ros2_pages.doctor_page.DoctorPage",
            ),
        ],
    ),
]
