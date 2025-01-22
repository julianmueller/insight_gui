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
        filterable: bool = True,
        css_classes: list[str] = None,
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

        self.filterable = filterable

        if css_classes is not None:
            for css_class in css_classes:
                super().add_css_class(css_class)

    @property
    def filter_text(self) -> str:
        return f"{super().get_title()} {super().get_subtitle()}"

    def set_prefix_icon(self, icon_name: str):
        self.prefix_icon.set_from_icon_name(icon_name)
        self.prefixes.set_visible(True)

    def add_suffix_btn(
        self,
        label: str | None = None,
        icon_name: str | None = None,
        tooltip_text: str | None = None,
        func: Callable = None,
        **func_kwargs,
    ):
        btn = Gtk.Button()
        if label:
            btn.set_label(label)
        if icon_name:
            btn.set_icon_name(icon_name)
        if tooltip_text:
            btn.set_tooltip_text(tooltip_text)

        btn.connect("clicked", lambda *_: func(**func_kwargs))
        self._add_suffix_widget(btn)

    def add_copy_btn(self, copy_text: str = "", tooltip_text: str = "Copy to clipboard", toast_host: Gtk.Widget = None):
        if not copy_text or copy_text is None:
            copy_text = super().get_title()

        self.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text=tooltip_text,
            func=self.on_copy_button_clicked,
            text=copy_text,
            toast_host=toast_host,
        )

    def add_suffix_label(self, label_text: str):
        if len(label_text) == 0:
            label_text = "<i>empty string</i>"
        label = Gtk.Label(label=label_text, use_markup=True)
        self._add_suffix_widget(label)

    def _add_suffix_widget(self, widget: Gtk.Widget):
        self.suffix_list.append(widget)
        self.suffix_box.append(widget)
        self.suffix_box.reorder_child_after(self.next_page_icon, widget)

    def set_subpage_link(
        self, *, nav_view: Adw.NavigationView, subpage_class: type[Adw.NavigationPage], **subpage_kwargs
    ):
        def on_activate(*args):
            nav_view.push(subpage_class(nav_view=nav_view, **subpage_kwargs))

        super().connect("activated", on_activate)
        super().set_activatable(True)
        self.next_page_icon.set_visible(True)

    def on_copy_button_clicked(self, text: str, toast_host: Gtk.Widget = None):
        clip = super().get_clipboard()
        clip.set(str(text))

        if toast_host is not None:
            toast_host.add_toast(Adw.Toast(title=f"Copied '{text}' to clipboard"))


def empty_pref_row(title: str = "empty list", subtitle: str = ""):
    return PrefRow(title=title, subtitle=subtitle, prefix_icon="dialog-error-symbolic", css_classes=["dim-label"])


# TODO add a button row?
# https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.1/class.ButtonRow.html
