from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


from insight_gui.utils.adw_colors import AdwAccentColor
from insight_gui.widgets.buttons import RevealButton
from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.ros2_pages.topic_info_page import TopicInfoPage


class BaseBlock(Adw.Bin):
    __gtype_name__ = "BaseBlock"

    def __init__(self, label: str, accent_color: AdwAccentColor = None, **kwargs):
        super().__init__()
        super().connect("realize", self.on_realize)

        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(Path(__file__).with_suffix(".ui")))

        self.main_box: Gtk.Box = builder.get_object("main_box")
        self.set_child(self.main_box)

        self.header_box: Gtk.Box = builder.get_object("header_box")
        self.header_lbl: Gtk.Label = builder.get_object("header_lbl")
        self.header_lbl.set_label(label)
        self.subpage_btn: Gtk.Button = builder.get_object("subpage_btn")
        self.subpage_btn.connect("clicked", self.on_subpage_btn_clicked)

        self.revealer: Gtk.Revealer = builder.get_object("revealer")
        self.content_box: Gtk.Box = builder.get_object("content_box")
        self.left_box: Gtk.Box = builder.get_object("left_box")
        self.right_box: Gtk.Box = builder.get_object("right_box")

        self.reveal_btn: RevealButton = RevealButton(self.revealer)
        self.header_box.prepend(self.reveal_btn)
        # self.label.set_cursor(Gdk.Cursor.new_from_name("grab"))

        if accent_color is not None and isinstance(accent_color, AdwAccentColor):
            self.main_box.add_css_class(accent_color.as_css_name())

    @property
    def width(self):
        return super().get_width()

    @property
    def height(self):
        return super().get_height()

    def on_realize(self, *args):
        self.nav_view = super().get_ancestor(Adw.NavigationView)
        self.ros2_connector = super().get_root().ros2_connector

    def on_subpage_btn_clicked(self, button, *args):
        pass


class NodeBlock(BaseBlock):
    __gtype_name__ = "NodeBlock"

    def __init__(self, node_full_name: str, **kwargs):
        super().__init__(label=node_full_name, accent_color=AdwAccentColor.ADW_ACCENT_COLOR_BLUE, **kwargs)
        self.node_full_name = node_full_name

    def on_realize(self, *args):
        super().on_realize()

    def on_subpage_btn_clicked(self, button, *args):
        self.nav_view.push(NodeInfoPage(self.node_full_name))


class InterfaceBlock(BaseBlock):
    __gtype_name__ = "InterfaceBlock"

    def __init__(self, interface_name: str, **kwargs):
        super().__init__(label=interface_name, accent_color=AdwAccentColor.ADW_ACCENT_COLOR_GREEN, **kwargs)
        self.interface_name = interface_name


class TopicBlock(BaseBlock):
    __gtype_name__ = "TopicBlock"

    def __init__(self, topic_name: str, topic_types: str | list[str], **kwargs):
        super().__init__(label=topic_name, accent_color=AdwAccentColor.ADW_ACCENT_COLOR_ORANGE, **kwargs)
        self.topic_name = topic_name
        self.topic_types = topic_types

    def on_realize(self, *args):
        super().on_realize()

    def on_subpage_btn_clicked(self, button, *args):
        self.nav_view.push(TopicInfoPage(self.topic_name, self.topic_types))


class ServiceBlock(BaseBlock):
    __gtype_name__ = "ServiceBlock"

    def __init__(self, service_name: str, **kwargs):
        super().__init__(label=service_name, **kwargs)
        self.service_name = service_name


class ActionBlock(BaseBlock):
    __gtype_name__ = "ActionBlock"

    def __init__(self, action_name: str, **kwargs):
        super().__init__(label=action_name, **kwargs)
        self.action_name = action_name


# class ParameterBlock(BaseBlock):
#     __gtype_name__ = "ParameterBlock"
#
#     def __init__(self, label: str, **kwargs):
#         super().__init__(label, **kwargs)
