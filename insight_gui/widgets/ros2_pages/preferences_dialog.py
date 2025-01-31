import os
import webbrowser

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_node import ROS2CommunicationNode
from insight_gui.widgets.helpers.pref_page import PrefPage
from insight_gui.widgets.helpers.pref_row import PrefRow
from insight_gui.widgets.helpers.button_row import ButtonRow

# TODO add setting to show/hide hidden nodes/topics etc


class PreferencesDialog(Adw.PreferencesDialog):
    __gtype_name__ = "PreferencesDialog"

    def __init__(self, ros2_node: ROS2CommunicationNode = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Settings")
        super().connect("map", self.on_map)

        self.ros2_node = ros2_node if ros2_node else self.get_root().ros2_node

        # Page with ROS2 Settings
        self.ros2_page = PrefPage(title="ROS2 Node", icon_name="applications-other-symbolic")
        super().add(self.ros2_page)

        # Group with ENV variables
        env_group = self.ros2_page.add_group(title="Environment Variables")
        env_group.add_btn(
            icon_name="info-symbolic",
            tooltip_text="ROS Documentation",
            func=lambda: webbrowser.open(
                "https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html#improveddynamicdiscovery"
            ),
        )

        self.env_auto_discovery_row = env_group.add_row(
            Adw.EntryRow(
                title="ROS_AUTOMATIC_DISCOVERY_RANGE",
                tooltip_text="choose between 'SUBNET', 'LOCALHOST', 'OFF', 'SYSTEM_DEFAULT'",
            )
        )
        self.env_static_peers_row = env_group.add_row(
            Adw.EntryRow(title="ROS_STATIC_PEERS", tooltip_text="list of IPs/domains, separated by ';'")
        )
        # self.env_static_peers_row.connect("notify::value")  # , lambda *_: self.on_static_peers_changed=True)
        self.env_domain_id_row = env_group.add_row(
            Adw.EntryRow(title="ROS_DOMAIN_ID", tooltip_text="unique number between 0 and 100")
        )
        self.env_discovery_server_row = env_group.add_row(Adw.EntryRow(title="ROS_DISCOVERY_SERVER", tooltip_text=""))
        self.env_apply_row = env_group.add_row(
            ButtonRow(
                title="Apply",
                tooltip_text="Apply Environment Variables",
                func=self.on_apply_env_vars,
            )
        )

        # controls_row: PrefRow = env_group.add_row(PrefRow(title="Controls"))
        # controls_row.add_suffix_btn(
        #     icon_name="media-playback-start-symbolic", tooltip_text="Start", func=self.on_start_ros2_node
        # )
        # controls_row.add_suffix_btn(
        #     icon_name="media-playback-stop-symbolic", tooltip_text="Stop", func=self.on_stop_ros2_node
        # )
        # controls_row = status_group.add_row(PrefRow(title="Controls"))

        # status_group = self.ros2_page.add_group(title="ROS2 Node Controls", description="bla")
        # status_row = status_group.add_row(
        #     PrefRow(title="Status", subtitle="", css_classes=["property"])  # ros2_node.get_status()
        # )
        # controls_row: PrefRow = status_group.add_row(PrefRow(title="Controls"))
        # controls_row.add_suffix_btn(
        #     icon_name="media-playback-start-symbolic", tooltip_text="Start", func=self.on_start_ros2_node
        # )
        # controls_row.add_suffix_btn(
        #     icon_name="media-playback-stop-symbolic", tooltip_text="Stop", func=self.on_stop_ros2_node
        # )
        # controls_row = status_group.add_row(PrefRow(title="Controls"))

        # settings_group = self.ros2_page.add_group(title="Settings", description="bla")
        # row_node_name = settings_group.add_row(Adw.EntryRow(title="ros2_gui_node_name", show_apply_button=True))
        # row_hide_node = settings_group.add_row(Adw.SwitchRow(title="Hide Node"))
        # row_node_namespace = settings_group.add_row(Adw.EntryRow(title="ros2_node_namespace", show_apply_button=True))
        # row_network_id = settings_group.add_row(Adw.EntryRow(title="ros2_network_id", show_apply_button=True))
        # row_apply_btn: PrefRow = settings_group.add_row(PrefRow(title="Apply Changes"))  # TODO make a ButtonRow
        # row_apply_btn.add_suffix_btn(
        #     icon_name="document-save-symbolic", tooltip_text="Save", func=self.on_apply_changes
        # )

        # row_apply_btn.connect("clicked", on_apply_changes)

        self.page2 = PrefPage(title="Others", icon_name="applications-engineering-symbolic")
        self.add(self.page2)

        self.page2.add_group(title="Test", description="bla")

    def on_map(self, *args):
        env_auto_discovery = os.getenv("ROS_AUTOMATIC_DISCOVERY_RANGE", default="")
        self.env_auto_discovery_row.set_text(env_auto_discovery)

        env_static_peers = os.getenv("ROS_STATIC_PEERS", default="")
        self.env_static_peers_row.set_text(env_static_peers)

        env_domain_id = os.getenv("ROS_DOMAIN_ID", default="")
        self.env_domain_id_row.set_text(env_domain_id)

        env_discovery_server = os.getenv("ROS_DISCOVERY_SERVER", default="")
        self.env_discovery_server_row.set_text(env_discovery_server)

    def on_apply_env_vars(self, *args):
        self.ros2_node.stop_node()

        os.environ["ROS_AUTOMATIC_DISCOVERY_RANGE"] = self.env_auto_discovery_row.get_text()
        os.environ["ROS_STATIC_PEERS"] = self.env_static_peers_row.get_text()
        os.environ["ROS_DOMAIN_ID"] = self.env_domain_id_row.get_text()
        os.environ["ROS_DISCOVERY_SERVER"] = self.env_discovery_server_row.get_text()

        self.add_toast(Adw.Toast(title="Applied Environment Variables"))
        self.ros2_node.start_node()

    def on_apply_changes(self, *args):
        # print(row_node_name.get_title())
        # print(row_hide_node.get_active())
        # print(row_node_namespace.get_title())
        # print(row_network_id.get_title())

        is_running_str = "running" if self.ros2_node.is_running else "not running"

        self.add_toast(Adw.Toast(title=f"ROS2 Node is {is_running_str}"))

    def on_start_ros2_node(self, *args):
        self.ros2_node.start_node()
        self.add_toast(Adw.Toast(title="Started ROS2 Node"))

    def on_stop_ros2_node(self, *args):
        self.ros2_node.stop_node()
        self.add_toast(Adw.Toast(title="Stopped ROS2 Node"))
