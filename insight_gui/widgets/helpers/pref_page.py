from pathlib import Path
import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.helpers.pref_group import PrefGroup


@Gtk.Template(filename=str(Path(__file__).with_suffix(".ui")))
class PrefPage(Adw.PreferencesPage):
    __gtype_name__ = "PrefPage"

    def __init__(
        self, title: str = "Preferences", icon_name: str = "settings-symbolic", description: str = "", **kwargs
    ):
        super().__init__(**kwargs)
        super().set_title(str(title))
        super().set_icon_name(icon_name)

        if description:
            super().set_description(str(description))

        self.groups: list[PrefGroup] = []

        # NOTE a pref page can also have a description!

    @property
    def num_groups(self) -> int:
        return len(self.groups)

    @property
    def is_empty(self) -> bool:
        return self.num_groups == 0

    def add(self, *args, **kwargs):
        raise NotImplementedError("use 'add_group' instead")

    def add_group(self, **kwargs) -> PrefGroup:
        pref_group = PrefGroup(**kwargs)
        super().add(pref_group)
        self.groups.append(pref_group)
        return pref_group

    def remove_group(self, pref_group: PrefGroup):
        super().remove(pref_group)
        self.groups.remove(pref_group)

    def clear(self):
        for pref_group in reversed(self.groups):
            self.remove_group(pref_group)
        # self.groups = []

    def apply_filter(self, text: str):
        # Check for empty search input
        if not text.strip():
            # Show all groups and rows if no text is provided
            for group in self.groups:
                group.set_visible(True)
                for row in group.rows:
                    row.set_visible(True)
            return

        # Compile the regex once for efficiency
        try:
            regex = re.compile(text, re.IGNORECASE)
        except re.error as e:
            print(f"Regex error: {e}")
            # If the regex is invalid, show all groups and rows
            for group in self.groups:
                group.set_visible(True)
                for row in group.rows:
                    row.set_visible(True)
            return

        # Filter groups and their rows
        for group in self.groups:
            group_title = group.get_title()
            group_description = group.get_description()  # Assuming groups have descriptions
            group_matches = (
                group_title and regex.search(group_title) or group_description and regex.search(group_description)
            )

            if group_matches:
                # If group matches, show all rows in the group
                group.set_visible(True)
                for row in group.rows:
                    row.set_visible(True)
            else:
                # If group does not match, filter rows individually
                group_visible = False
                for row in group.rows:
                    # TODO add a generic property to the rows, which strings to check when filtering, for custum rows,
                    # that dont have a title or description

                    row_title = row.get_title()
                    row_subtitle = row.get_subtitle()  # Assuming rows have subtitles
                    if row_title and regex.search(row_title) or row_subtitle and regex.search(row_subtitle):
                        row.set_visible(True)
                        group_visible = True  # Show the group if any row matches
                    else:
                        row.set_visible(False)
                group.set_visible(group_visible)
