from pathlib import Path
import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


@Gtk.Template(filename=str(Path(__file__).with_suffix(".ui")))
class TextViewRow(Adw.PreferencesRow):
    __gtype_name__ = "TextViewRow"

    main_box: Gtk.Box = Gtk.Template.Child()
    header_box: Gtk.Box = Gtk.Template.Child()
    title_label: Gtk.Label = Gtk.Template.Child()
    subtitle_label: Gtk.Label = Gtk.Template.Child()
    copy_button: Gtk.Button = Gtk.Template.Child()

    frame: Gtk.Frame = Gtk.Template.Child()
    scrolled: Gtk.ScrolledWindow = Gtk.Template.Child()
    text_view: Gtk.TextView = Gtk.Template.Child()

    def __init__(
        self,
        *,
        title: str = "",
        subtitle: str = "",
        min_height: int = -1,
        max_height: int = -1,
        show_copy_btn: bool = False,
        filterable: bool = True,
        editable: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.text_buffer = self.text_view.get_buffer()

        # Add title label if provided
        if title:
            self.title_label.set_text(str(title))
        else:
            self.title_label.set_visible(False)

        # Add subtitle label if provided
        if subtitle:
            self.subtitle_label.set_text(str(subtitle))
        else:
            self.subtitle_label.set_visible(False)

        if not title and not subtitle:
            self.header_box.set_visible(False)

        if editable:
            self.text_view.set_editable(True)

        self.filterable = filterable
        self.toggle_copy_button_visibility(show_copy_btn)
        self.scrolled.set_min_content_height(min_height)
        self.scrolled.set_max_content_height(max_height)

    @property
    def line_count(self) -> int:
        return self.text_buffer.get_line_count()

    @property
    def filter_text(self) -> str:
        return f"{self.title_label.get_text()} {self.subtitle_label.get_text()} {self.get_text()}"

    def set_title(self, title: str):
        self.title_label.set_label(str(title))
        self.title_label.set_visible(len(str(title)) > 0)
        self.header_box.set_visible(len(self.title_label.get_label()) > 0 or len(self.subtitle_label.get_label()) > 0)

    def set_subtitle(self, subtitle: str):
        self.subtitle_label.set_label(str(subtitle))
        self.subtitle_label.set_visible(len(str(subtitle)) > 0)
        self.header_box.set_visible(len(self.title_label.get_label()) > 0 or len(self.subtitle_label.get_label()) > 0)

    def get_text(self) -> str:
        start_iter = self.text_buffer.get_start_iter()
        end_iter = self.text_buffer.get_end_iter()
        return self.text_buffer.get_text(start_iter, end_iter, True)

    def set_text(self, text: str):
        self.text_buffer.set_text(str(text).rstrip())

    def append_text(self, text: str):
        self.text_buffer.insert(self.text_buffer.get_end_iter(), str(text))

    def append_tagged_text(self, text: str, tag: str):
        # self.add_tag(tag)
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), str(text), str(tag))

    def prepend_text(self, text: str):
        self.text_buffer.insert(self.text_buffer.get_start_iter(), str(text))

    def prepend_tagged_text(self, text: str, tag: str):
        # self.add_tag(tag)
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_start_iter(), str(text), str(tag))

    def clear(self):
        self.text_buffer.set_text("")

    def add_tag(self, tag: str, **prop_kwargs):
        if not self.text_buffer.get_tag_table().lookup(str(tag)):
            self.text_buffer.create_tag(str(tag), **prop_kwargs)

    def add_tags(self, tags: list[str], **prop_kwargs):
        for tag in tags:
            self.add_tag(tag, **prop_kwargs)

    def scroll_to_end(self):
        self.text_view.scroll_to_iter(self.text_buffer.get_end_iter(), 0, False, 0, 1)

    def fit_height_to_text(self):
        _, natural_size = self.text_view.get_preferred_size()
        self.scrolled.set_min_content_height(natural_size.height)
        self.scrolled.set_max_content_height(natural_size.height)

    # TODO do the filtering with GtkTextTags
    def filter_text(self, filter_snippets: list[str]):
        # Get the current text from the buffer
        start_iter = self.text_buffer.get_start_iter()
        end_iter = self.text_buffer.get_end_iter()
        current_text = self.text_buffer.get_text(start_iter, end_iter, True)

        # Split the text into lines
        lines = current_text.splitlines()

        # Create a list to store matching lines
        filtered_lines = []

        # Check each line against the search patterns
        for line in lines:
            # Split the search text into patterns
            patterns = [pattern for pattern in filter_snippets if pattern]

            # Check if any pattern matches the current line
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    filtered_lines.append(line)
                    break

        # Join the filtered lines and update the text buffer
        result_text = "\n".join(filtered_lines)
        self.text_buffer.set_text(result_text)

    def filter_by_tags(self, tag_names: list[str]):
        tag_table = self.text_buffer.get_tag_table()
        tag_table.foreach(lambda tag: print(tag.get_property("name")))

        def toggle_tag_visibility(tag):
            if tag.get_property("name") not in tag_names:
                tag.set_property("invisible", True)
            else:
                tag.set_property("invisible", False)

        tag_table.foreach(lambda tag: toggle_tag_visibility(tag))

    def toggle_copy_button_visibility(self, visible: bool):
        self.copy_button.set_visible(visible)

    @Gtk.Template.Callback()
    def on_copy_button_clicked(self, button):
        clip = self.get_clipboard()
        clip.set(str(self.get_text()))
