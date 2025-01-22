import re

from ros2doctor.api import generate_reports

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_node import ROS2CommunicationNode
from insight_gui.widgets.helpers.content_page import ContentPage
from insight_gui.widgets.helpers.pref_row import PrefRow


class DoctorPage(Adw.NavigationPage):
    __gtype_name__ = "DoctorPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_node: ROS2CommunicationNode = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Doctor")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_node = ros2_node if ros2_node else self.get_root().ros2_node

        self.content_page = ContentPage(refresh_func=self.refresh)
        self.content_page.set_search_entry_placeholder_text("Ask the doctor")
        super().set_child(self.content_page)

        self.network_config_group = self.content_page.pref_page.add_group(title="NETWORK CONFIGURATION")
        self.package_versions_group = self.content_page.pref_page.add_group(title="PACKAGE VERSIONS")
        self.platform_info_group = self.content_page.pref_page.add_group(title="PLATFORM INFORMATION")
        self.qos_compatibility_group = self.content_page.pref_page.add_group(title="QOS COMPATIBILITY LIST")
        self.rmw_info_group = self.content_page.pref_page.add_group(title="RMW MIDDLEWARE")
        self.ros2_info_group = self.content_page.pref_page.add_group(title="ROS 2 INFORMATION")
        self.topic_list_group = self.content_page.pref_page.add_group(title="TOPIC LIST", empty_msg="No topics found")

    def refresh(self, *args) -> bool:
        if not self.ros2_node.is_running:
            # TODO now, the msg "refresh yielded no result" shows up, make it, that refresh is restarted
            self.content_page.show_toast_w_btn("ROS2 node not running", "Start Node", func=self.ros2_node.start_node)
            return False

        self.network_config_group.clear()
        self.package_versions_group.clear()
        self.platform_info_group.clear()
        self.qos_compatibility_group.clear()
        self.rmw_info_group.clear()
        self.ros2_info_group.clear()
        self.topic_list_group.clear()

        reports = generate_reports()

        for report in reports:
            if report.name == "NETWORK CONFIGURATION":
                for item in report.items:
                    self.network_config_group.add_row(PrefRow(title=item[0], subtitle=item[1]))

            elif report.name == "PACKAGE VERSIONS":
                for item in report.items:
                    row: PrefRow = self.package_versions_group.add_row(PrefRow(title=item[0], subtitle=item[1]))

                    re_match = re.match(r"^latest\=([^,]+), local\=([^,]+)$", item[1])
                    latest_version = re_match.group(1).strip()
                    local_version = re_match.group(2).strip()
                    if latest_version != local_version:
                        row.set_prefix_icon("software-update-available-symbolic")

            elif report.name == "PLATFORM INFORMATION":
                for item in report.items:
                    self.platform_info_group.add_row(PrefRow(title=item[0], subtitle=item[1]))

            elif report.name == "QOS COMPATIBILITY LIST":
                for item in report.items:
                    self.qos_compatibility_group.add_row(PrefRow(title=item[0], subtitle=item[1]))

            elif report.name == "RMW MIDDLEWARE":
                for item in report.items:
                    self.rmw_info_group.add_row(PrefRow(title=item[0], subtitle=item[1]))

            elif report.name == "ROS 2 INFORMATION":
                for item in report.items:
                    row = self.ros2_info_group.add_row(PrefRow(title=item[0], subtitle=item[1]))
                    row.add_copy_btn(copy_text=row.get_subtitle(), toast_host=self.content_page.toast_overlay)

            elif report.name == "TOPIC LIST":
                for item in report.items:
                    self.topic_list_group.add_row(PrefRow(title=item[0], subtitle=item[1]))

        return bool(self.content_page.pref_page.num_groups)


# TODO add NetworkHelloPage for 'ros2 doctor hello'
