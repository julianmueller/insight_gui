from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


from insight_gui.utils.adw_colors import AdwAccentColor


class BaseBlock(Adw.Bin):
    __gtype_name__ = "BaseBlock"

    def __init__(self, label: str, accent_color: AdwAccentColor = None, **kwargs):
        super().__init__()

        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(Path(__file__).with_suffix(".ui")))

        self.main_box: Gtk.Box = builder.get_object("main_box")
        self.set_child(self.main_box)

        self.header_box: Gtk.Box = builder.get_object("header_box")
        self.header_lbl: Gtk.Label = builder.get_object("header_lbl")
        self.header_lbl.set_label(label)
        self.header_btn: Gtk.Button = builder.get_object("header_btn")
        self.header_btn.connect("clicked", self.on_header_btn_clicked)
        self.content_box: Gtk.Box = builder.get_object("content_box")
        self.left_box: Gtk.Box = builder.get_object("left_box")
        self.right_box: Gtk.Box = builder.get_object("right_box")

        # self.label.set_cursor(Gdk.Cursor.new_from_name("grab"))

        if accent_color is not None and isinstance(accent_color, AdwAccentColor):
            self.main_box.add_css_class(accent_color.as_css_name())

    def on_header_btn_clicked(self, button):
        print("header button clicked")


class NodeBlock(BaseBlock):
    __gtype_name__ = "NodeBlock"

    def __init__(self, label: str, **kwargs):
        super().__init__(label, accent_color=AdwAccentColor.ADW_ACCENT_COLOR_BLUE, **kwargs)


class InterfaceBlock(BaseBlock):
    __gtype_name__ = "InterfaceBlock"

    def __init__(self, label: str, **kwargs):
        super().__init__(label, accent_color=AdwAccentColor.ADW_ACCENT_COLOR_GREEN, **kwargs)


class TopicBlock(BaseBlock):
    __gtype_name__ = "TopicBlock"

    def __init__(self, label: str, **kwargs):
        super().__init__(label, accent_color=AdwAccentColor.ADW_ACCENT_COLOR_ORANGE, **kwargs)


class ServiceBlock(BaseBlock):
    __gtype_name__ = "ServiceBlock"

    def __init__(self, label: str, **kwargs):
        super().__init__(label, **kwargs)


class ActionBlock(BaseBlock):
    __gtype_name__ = "ActionBlock"

    def __init__(self, label: str, **kwargs):
        super().__init__(label, **kwargs)


# class ParameterBlock(BaseBlock):
#     __gtype_name__ = "ParameterBlock"
#
#     def __init__(self, label: str, **kwargs):
#         super().__init__(label, **kwargs)
