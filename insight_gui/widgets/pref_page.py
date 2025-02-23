from pathlib import Path
import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.pref_group import PrefGroup


class PrefPage(Adw.PreferencesPage):
    __gtype_name__ = "PrefPage"

    def __init__(
        self, title: str = "Preferences", icon_name: str = "settings-symbolic", description: str = "", **kwargs
    ):
        super().__init__(**kwargs)
        super().set_title(str(title))
        super().set_icon_name(icon_name)

        # NOTE a pref page can also have a description!
        if description:
            super().set_description(str(description))

        self.groups: list[PrefGroup] = []

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

    # TODO this causes some groups to reap
    def apply_filter(self, text: str):
        """Filters groups and rows based on a search query."""

        def reset_filtering():
            """Resets all groups and rows to their original visibility."""
            for group in self.groups:
                if not group.filterable:
                    continue
                group.set_unfiltered()
                for row in group.rows:
                    if getattr(row, "filterable", False):
                        row.set_unfiltered()

        # If the search text is empty, restore original visibility
        if not text.strip():
            reset_filtering()
            return

        try:
            regex = re.compile(text, re.IGNORECASE)
        except re.error as e:
            print(f"Regex error: {e}")
            reset_filtering()
            return

        # Filtering process
        for group in self.groups:
            if not group.filterable:
                continue

            group_matches = bool(group.filter_text and regex.search(group.filter_text))
            any_row_matches = False

            for row in group.rows:
                if not getattr(row, "filterable", False):
                    continue

                row_matches = bool(row.filter_text and regex.search(row.filter_text))
                if row_matches:
                    row.set_filtered(True)  # Show matching row
                    any_row_matches = True
                else:
                    row.set_filtered(False)  # Hide non-matching row

            # Show group if it matches or any row inside it matches
            group.set_filtered(group_matches or any_row_matches)
