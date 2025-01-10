from pathlib import Path
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


@Gtk.Template(filename=str(Path(__file__).with_suffix(".ui")))
class PrefRow(Adw.ActionRow):
    __gtype_name__ = "PrefRow"

    prefix_icon: Gtk.Image = Gtk.Template.Child()
    suffix_box: Gtk.Box = Gtk.Template.Child()
    next_page_icon: Gtk.Image = Gtk.Template.Child()

    def __init__(
        self,
        *,
        title: str = "",
        subtitle: str = "",
        is_hidden: bool = False,
        prefix_icon: str = "",
        suffix_lbl: str = "",
        css_classes: list[str] = [],
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().set_use_markup(False)
        super().set_title(str(title))
        super().set_subtitle(str(subtitle))

        self.prefixes = super().get_first_child().get_first_child()  # PrefRow -> header -> prefixes
        self.prefixes.set_visible(False)

        self.suffix_list = []

        if is_hidden:
            self.set_prefix_icon("eye-not-looking-symbolic")

        if prefix_icon:
            self.set_prefix_icon(prefix_icon)

        if str(suffix_lbl):
            self.add_suffix_label(str(suffix_lbl))

        for css_class in css_classes:
            super().add_css_class(css_class)

    def set_prefix_icon(self, icon_name: str):
        self.prefix_icon.set_from_icon_name(icon_name)
        self.prefixes.set_visible(True)

    def add_suffix_btn(self, icon_name: str, tooltip_text: str, func: Callable, **func_kwargs):
        btn = Gtk.Button.new_from_icon_name(icon_name)
        btn.set_tooltip_text(tooltip_text)
        btn.connect("clicked", lambda *_: func(**func_kwargs))
        self.add_suffix_widget(btn)

    def add_suffix_label(self, label_text: str):
        if len(label_text) == 0:
            label_text = "<i>empty string</i>"
        label = Gtk.Label(label=label_text, use_markup=True)
        self.add_suffix_widget(label)

    def add_suffix_widget(self, widget: Gtk.Widget):
        self.suffix_list.append(widget)
        self.suffix_box.append(widget)
        self.suffix_box.reorder_child_after(self.next_page_icon, widget)

    def set_subpage_link(
        self, *, nav_view: Adw.NavigationView, subpage_class: type[Adw.NavigationPage], **subpage_kwargs
    ):
        def on_activate(*args):
            nav_view.push(subpage_class(nav_view=nav_view, **subpage_kwargs))

        self.connect("activated", on_activate)
        self.set_activatable(True)
        self.next_page_icon.set_visible(True)


def empty_pref_row(title: str = "empty list", subtitle: str = ""):
    return PrefRow(title=title, subtitle=subtitle, prefix_icon="dialog-error-symbolic", css_classes=["dim-label"])
