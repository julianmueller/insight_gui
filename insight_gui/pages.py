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
import re

from gi.repository import GObject

from insight_gui.widgets.content_page import ContentPage
from insight_gui.ros2_pages.pkg_list_page import PackageListPage
from insight_gui.ros2_pages.node_list_page import NodeListPage
from insight_gui.ros2_pages.topic_list_page import TopicListPage
from insight_gui.ros2_pages.topic_pub_page import TopicPublisherPage
from insight_gui.ros2_pages.topic_sub_page import TopicSubscriberPage
from insight_gui.ros2_pages.service_list_page import ServiceListPage
from insight_gui.ros2_pages.service_call_page import ServiceCallPage
from insight_gui.ros2_pages.action_goal_page import ActionGoalPage
from insight_gui.ros2_pages.action_list_page import ActionListPage
from insight_gui.ros2_pages.launch_list_page import LaunchListPage
from insight_gui.ros2_pages.interface_browser_page import InterfaceBrowserPage
from insight_gui.ros2_pages.graph_page import GraphPage
from insight_gui.ros2_pages.param_list_page import ParameterListPage
from insight_gui.ros2_pages.tf_page import TransformsPage
from insight_gui.ros2_pages.tf_static_broadcaster_page import StaticTransformBroadcasterPage
from insight_gui.ros2_pages.tf_tree_page import TFTreePage
from insight_gui.ros2_pages.img_viewer_page import ImageViewerPage
from insight_gui.ros2_pages.joint_states_page import JointStatesPage
from insight_gui.ros2_pages.teleop_page import TeleoperatorPage
from insight_gui.ros2_pages.log_page import LoggerPage
from insight_gui.ros2_pages.doctor_page import DoctorPage
from insight_gui.ros2_pages.multicast_page import MulticastPage


class Page(GObject.Object):
    def __init__(
        self,
        *,
        title: str,
        subtitle: str,
        icon_name: str,
        page_id: str,
        group_id: str = "",
        nav_page_class: ContentPage,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._title = title
        self._subtitle = subtitle
        self._icon_name = icon_name
        self._page_id = page_id
        self._group_id = group_id
        self._nav_page_class = nav_page_class

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
    def nav_page_class(self) -> list:
        return self._nav_page_class

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

    @property
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


def create_pages():
    return [
        PageGroup(
            title="Packages",
            pages=[
                Page(
                    title="Packages",
                    subtitle="Browse all packages",
                    icon_name="package-symbolic",
                    page_id="pkg_list",
                    nav_page_class=PackageListPage,
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
                    nav_page_class=NodeListPage,
                ),
                Page(
                    title="Launch Files",
                    subtitle="Browse launch files",
                    icon_name="rocket-launch-symbolic",
                    page_id="launch_list",
                    nav_page_class=LaunchListPage,
                ),
                Page(
                    title="Parameters",
                    subtitle="Manage node parameters",
                    icon_name="instant-mix-symbolic",
                    page_id="param_list",
                    nav_page_class=ParameterListPage,
                ),
                Page(
                    title="Graph",
                    subtitle="ROS2 computational graph",
                    icon_name="graph3-symbolic",
                    page_id="graph_page",
                    nav_page_class=GraphPage,
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
                    nav_page_class=TopicListPage,
                ),
                Page(
                    title="Publisher",
                    subtitle="Publish to topics",
                    icon_name="rss-feed-symbolic",
                    page_id="topic_pub",
                    nav_page_class=TopicPublisherPage,
                ),
                Page(
                    title="Subscriber",
                    subtitle="Subscribe to topics",
                    icon_name="subscriptions-symbolic",
                    page_id="topic_sub",
                    nav_page_class=TopicSubscriberPage,
                ),
                Page(
                    title="Image Viewer",
                    subtitle="View image topics",
                    icon_name="image-x-generic-symbolic",
                    page_id="img_viewer",
                    nav_page_class=ImageViewerPage,
                ),
                # Page(
                #     title="Remap",
                #     subtitle="Remap topics",
                #     icon_name="tactic-symbolic",
                #     page_id="remap",
                #     nav_page_class=RemapPage,
                # ),
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
                    nav_page_class=ServiceListPage,
                ),
                Page(
                    title="Service Caller",
                    subtitle="Call services",
                    icon_name="call-start-symbolic",
                    page_id="srv_caller",
                    nav_page_class=ServiceCallPage,
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
                    nav_page_class=ActionListPage,
                ),
                Page(
                    title="Action Goal",
                    subtitle="Send action goals",
                    icon_name="emoji-flags-symbolic",
                    page_id="action_goal",
                    nav_page_class=ActionGoalPage,
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
                    nav_page_class=InterfaceBrowserPage,
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
                    nav_page_class=TransformsPage,
                ),
                Page(
                    title="Static Transform Broadcaster",
                    subtitle="Broadcast to /tf_static",
                    icon_name="bigtop-updates-symbolic",
                    page_id="tf_static_broadcaster",
                    nav_page_class=StaticTransformBroadcasterPage,
                ),
                Page(
                    title="TF-Tree",
                    subtitle="Inspect all TFs as a tree",
                    icon_name="forest-symbolic",
                    page_id="tf_tree",
                    nav_page_class=TFTreePage,
                ),
            ],
        ),
        PageGroup(
            title="Control",
            pages=[
                # Page(
                #     title="Controllers",
                #     subtitle="Toggle ros2control controllers",
                #     icon_name="memory-symbolic",
                #     page_id="controllers",
                #     nav_page_class=ControllerTogglePage,
                # ),
                Page(
                    title="Joint States",
                    subtitle="Manipulate joints",
                    icon_name="sliders-horizontal-symbolic",
                    page_id="joint_states",
                    nav_page_class=JointStatesPage,
                ),
                Page(
                    title="Teleoperator",
                    subtitle="Teleoperate a robot",
                    icon_name="gamepad-symbolic",
                    page_id="teleop",
                    nav_page_class=TeleoperatorPage,
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
                    nav_page_class=LoggerPage,
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
                    nav_page_class=MulticastPage,
                ),
                Page(
                    title="Doctor",
                    subtitle="System diagnostics",
                    icon_name="doctor-symbolic",
                    page_id="doctor",
                    nav_page_class=DoctorPage,
                ),
            ],
        ),
    ]
