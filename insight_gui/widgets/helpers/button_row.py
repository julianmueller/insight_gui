from pathlib import Path
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


@Gtk.Template(filename=str(Path(__file__).with_suffix(".ui")))
class ButtonRow(Adw.PreferencesRow):
    __gtype_name__ = "ButtonRow"

    box: Gtk.Box = Gtk.Template.Child()
    start_icon: Gtk.Image = Gtk.Template.Child()
    btn: Gtk.Button = Gtk.Template.Child()
    end_icon: Gtk.Image = Gtk.Template.Child()

    def __init__(
        self,
        *,
        title: str = "",
        start_icon_name: str = "",
        end_icon_name: str = "",
        tooltip_text: str = "",
        func: Callable = None,
        func_kwargs: dict = None,
        css_classes: list[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().get_first_child().get_first_child().get_next_sibling().get_next_sibling().set_visible(False)
        # PrefRow -> header -> prefixes -> image -> title_box
        # super().set_activatable_widget(self.btn)

        if title:
            self.btn.set_label(str(title))

        if start_icon_name:
            self.start_icon.set_from_icon_name(start_icon_name)
            self.start_icon.set_visible(True)

        if end_icon_name:
            self.end_icon.set_from_icon_name(end_icon_name)
            self.end_icon.set_visible(True)

        if tooltip_text:
            self.btn.set_tooltip_text(tooltip_text)

        if func:
            func_kwargs = {} if func_kwargs is None else func_kwargs
            self.set_func(func, **func_kwargs)

        if css_classes is not None:
            for css_class in css_classes:
                super().add_css_class(css_class)

    def set_func(self, func: Callable, **func_kwargs):
        self.func = func
        self.func_kwargs = func_kwargs

    @Gtk.Template.Callback()
    def on_clicked(self, *args):
        self.func(**self.func_kwargs)
