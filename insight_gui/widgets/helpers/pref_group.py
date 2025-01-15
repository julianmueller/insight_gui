from pathlib import Path
import re
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.helpers.pref_row import empty_pref_row


@Gtk.Template(filename=str(Path(__file__).with_suffix(".ui")))
class PrefGroup(Adw.PreferencesGroup):
    __gtype_name__ = "PrefGroup"

    suffix_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, *, title: str = "", description: str = "", empty_msg: str = "empty list", **kwargs):
        super().__init__(**kwargs)
        super().set_title(str(title))
        super().set_description(str(description))

        self.rows: list[Adw.ActionRow] = []
        self.suffix_btns: list[Gtk.Button] = []

        if not title and not description:
            super().get_first_child().get_first_child().set_visible(False)  # disable group header

        self.empty_row = empty_pref_row(title=str(empty_msg))
        super().add(self.empty_row)

    @property
    def num_rows(self):
        return len(self.rows)

    @property
    def is_empty(self):
        return self.num_rows == 0

    def add(self, *args, **kwargs):
        raise NotImplementedError("use 'add_row' instead")

    def add_row(self, row: Gtk.Widget) -> Gtk.Widget:
        self.empty_row.set_visible(False)
        super().add(row)
        self.rows.append(row)
        return row

    def remove_row(self, row: Gtk.Widget):
        super().remove(row)
        self.rows = [_row for _row in self.rows if _row != row]

    def clear(self):
        for row in reversed(self.rows):
            self.remove_row(row)
        self.empty_row.set_visible(True)

    def add_btn(self, *, icon_name: str, tooltip_text: str, visible: bool = True, func: Callable, **func_kwargs):
        btn = Gtk.Button.new_from_icon_name(icon_name)
        btn.set_visible(visible)
        btn.set_tooltip_text(tooltip_text)
        btn.connect("clicked", lambda *_: func(**func_kwargs))
        btn.add_css_class("flat")

        self.suffix_box.append(btn)  # add to gtk box
        self.suffix_btns.append(btn)  # add to internal list of btns
        self.suffix_box.set_visible(True)

    def set_description_to_row_count(self):
        super().set_description(f"Count: {self.num_rows}")

    def set_empty_row_title(self, empty_msg: str):
        self.empty_row.set_title(empty_msg)

    # TODO i think, this is obsolete, as the filter is now done per page
    def apply_filter(self, text: str):
        # Compile the regex once for efficiency
        try:
            regex = re.compile(text, re.IGNORECASE)
        except re.error as e:
            ros2_node = self.get_root().ros2_node
            if ros2_node:
                ros2_node.get_logger().error(f"Regex error: {e}", once=True)
            else:
                print(f"Regex error: {e}")

            # If the regex is invalid, show all rows
            for row in self.rows:
                row.set_visible(True)
            return

        for row in self.rows:
            title = row.get_title()
            subtitle = row.get_subtitle()
            if title and regex.search(title) or subtitle and regex.search(subtitle):
                row.set_visible(True)
            else:
                row.set_visible(False)
