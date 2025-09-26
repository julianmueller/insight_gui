# =============================================================================
# pref_rows.py
#
# This file is part of https://github.com/julianmueller/insight_gui
# Copyright (C) 2025 Julian Müller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
# =============================================================================

from typing import Callable, Type
import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GObject, Gtk, Adw, Gdk, GLib, Gio, Pango

from insight_gui.widgets.buttons import ToggleButton, CopyButton


class PrefRowInterface(GObject.GObject):
    """Interface Class for common row properties."""

    __gtype_name__ = "PrefRowInterface"

    def __init__(self):
        super().__init__()
        self._filter_text = ""
        self._tags: set[str] = set()

        # Store initial visibility
        self._is_filtered = False
        self._visibility_before_filter = self.get_visible()

    @GObject.Property(type=bool, default=False)
    def filterable(self) -> bool:
        return bool(self.filter_text)

    @GObject.Property(type=str, default="")
    def filter_text(self) -> str:
        return self._filter_text.lower()

    @filter_text.setter
    def filter_text(self, value: str):
        self._filter_text = str(value).lower()

    @GObject.Property(type=bool, default=False)
    def is_filtered(self) -> bool:
        return self._is_filtered

    def has_tag(self, tag) -> bool:
        return tag in self._tags

    def add_tag(self, tag):
        self._tags.add(tag)

    def remove_tag(self, tag):
        self._tags.discard(tag)

    # filters (hides) the row but remembers its original visibility
    def set_filtered(self, visible: bool) -> bool:
        if not self._is_filtered:
            self._visibility_before_filter = self.get_visible()

        if self._visibility_before_filter:
            self.set_visible(visible)

        self._is_filtered = True

    # restores original visibility before the filtering
    def set_unfiltered(self):
        if self._is_filtered:
            self.set_visible(self._visibility_before_filter)
            self._is_filtered = False


class PrefRow(Adw.ActionRow, PrefRowInterface):
    __gtype_name__ = "PrefRow"

    def __init__(
        self,
        *,
        title: str = "",
        subtitle: str = "",
        css_classes: list[str] = [],
        tags: list[str] = [],
        **kwargs,
    ):
        Adw.ActionRow.__init__(self, **kwargs)
        PrefRowInterface.__init__(self)
        super().set_use_markup(False)

        self.header_box: Gtk.Box = self.get_first_child()
        self.prefixes_box: Gtk.Box = self.header_box.get_first_child()
        self.header_image: Gtk.Image = self.prefixes_box.get_next_sibling()
        self.title_box: Gtk.Box = self.header_image.get_next_sibling()
        self.suffixes_box: Gtk.Image = self.title_box.get_next_sibling()

        # self.prefixes_box.set_visible(False)
        # self.suffixes_box.set_visible(False)

        self.title_lbl: Gtk.Label = self.title_box.get_first_child()
        self.title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_lbl.set_hexpand(True)
        self.title_lbl.set_halign(Gtk.Align.FILL)
        self.title_lbl.set_single_line_mode(True)
        # fixes: reported min width 12 and natural width 10 in measure() with for_size=16; natural size must be >= min size
        self.title_lbl.set_width_chars(12)

        self.subtitle_lbl: Gtk.Label = self.title_lbl.get_next_sibling()
        self.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.subtitle_lbl.set_hexpand(True)
        self.subtitle_lbl.set_halign(Gtk.Align.FILL)
        self.subtitle_lbl.set_single_line_mode(True)
        # fixes: reported min width 12 and natural width 10 in measure() with for_size=16; natural size must be >= min size
        self.subtitle_lbl.set_width_chars(12)

        # react to hide header
        if not title and not subtitle:
            self.title_box.set_visible(False)
        super().set_title(str(title))
        super().set_subtitle(str(subtitle))

        for css_class in css_classes:
            super().add_css_class(css_class)

        for tag in tags:
            self.add_tag(tag)

        self.next_page_icon: Gtk.Image = Gtk.Image(icon_name="go-next-symbolic", visible=False)
        self.add_suffix(self.next_page_icon)

    @GObject.Property(type=str, default="")
    def filter_text(self) -> str:
        return f"{super().get_title()} {super().get_subtitle()}".lower()

    def add_prefix(self, widget: Gtk.Widget, *, prepend: bool = False) -> Gtk.Widget:
        if prepend:
            self.prefixes_box.prepend(widget)
        else:
            self.prefixes_box.append(widget)
        self.prefixes_box.set_visible(True)
        return widget

    def add_prefix_lbl(self, label: str, *, prepend: bool = False, **kwargs) -> Gtk.Label:
        return self.add_prefix(Gtk.Label(label=label, **kwargs), prepend=prepend)

    def add_prefix_icon(self, icon_name: str, *, tooltip_text: str = "", prepend: bool = False, **kwargs) -> Gtk.Image:
        return self.add_prefix(
            Gtk.Image(icon_name=icon_name, tooltip_text=tooltip_text, **kwargs),
            prepend=prepend,
        )

    def add_prefix_btn(
        self,
        *,
        icon_name: str,
        func: Callable,
        func_kwargs: dict = {},
        tooltip_text: str = "",
        prepend: bool = False,
        **kwargs,
    ) -> Gtk.Button:
        btn = Gtk.Button(
            icon_name=icon_name,
            tooltip_text=tooltip_text,
            vexpand=False,
            valign=Gtk.Align.CENTER,
            **kwargs,
        )
        btn.connect("clicked", lambda *_: func(**func_kwargs))
        return self.add_prefix(btn, prepend=prepend)

    def add_suffix(self, widget: Gtk.Widget, *, prepend: bool = False) -> Gtk.Widget:
        if prepend:
            self.suffixes_box.prepend(widget)
        else:
            self.suffixes_box.append(widget)
            self.suffixes_box.reorder_child_after(self.next_page_icon, widget)

        self.suffixes_box.set_visible(True)
        return widget

    def add_suffix_lbl(self, label: str, *, prepend: bool = False, **kwargs) -> Gtk.Label:
        return self.add_suffix(Gtk.Label(label=label, **kwargs), prepend=prepend)

    def add_suffix_icon(self, icon_name: str, *, tooltip_text: str = "", prepend: bool = False, **kwargs) -> Gtk.Image:
        return self.add_suffix(
            Gtk.Image(icon_name=icon_name, tooltip_text=tooltip_text, **kwargs),
            prepend=prepend,
        )

    def add_suffix_btn(
        self,
        *,
        icon_name: str,
        func: Callable,
        func_kwargs: dict = {},
        tooltip_text: str = "",
        prepend: bool = False,
        **kwargs,
    ) -> Gtk.Button:
        btn = Gtk.Button(
            icon_name=icon_name,
            tooltip_text=tooltip_text,
            vexpand=False,
            valign=Gtk.Align.CENTER,
            **kwargs,
        )
        btn.connect("clicked", lambda *_: func(**func_kwargs))
        return self.add_suffix(btn, prepend=prepend)

    def set_subpage_link(
        self, *, nav_view: Adw.NavigationView, subpage_class: Type[Adw.NavigationPage], subpage_kwargs: dict
    ):
        def _on_pressed(controller: Gtk.GestureClick, n_press: int, x: float, y: float):
            state = controller.get_current_event_state()
            subpage = subpage_class(**subpage_kwargs)

            # add CTRL+click functionality to open in detached window
            if state & Gdk.ModifierType.CONTROL_MASK:
                subpage.detach()

            # regular click
            else:
                nav_view.push(subpage)

        # if hasattr(self, "subpage_signal_handler"):
        #     super().disconnect(self.subpage_signal_handler)

        self.gesture_click = Gtk.GestureClick()
        self.subpage_signal_handler = self.gesture_click.connect("pressed", _on_pressed)
        super().add_controller(self.gesture_click)

        super().set_activatable(True)
        self.next_page_icon.set_visible(True)

    def set_subtitle(self, subtitle: str, max_lines: int = 1):
        # TODO concat lines of the subtitle!
        # if len(subtitle)
        # subtitle =
        super().set_subtitle(subtitle)


class ScaleRow(PrefRow):
    __gtype__name__ = "ScaleRow"
    __gsignals__ = {"value-changed": (GObject.SignalFlags.RUN_FIRST, None, (float,))}

    def __init__(
        self, value: float = 0, lower: float = 0, upper: float = 10, step: float = 1, num_digits: int = 0, **kwargs
    ):
        super().__init__(**kwargs)
        self.header_box.set_hexpand(False)
        self.title_lbl.set_hexpand(False)
        self.subtitle_lbl.set_hexpand(False)

        self.scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=Gtk.Adjustment(value=value, lower=lower, upper=upper, step_increment=step),
            draw_value=True,
            digits=num_digits,
            hexpand=True,
            value_pos=Gtk.PositionType.RIGHT,
        )
        self.minus_button = Gtk.Button(icon_name="minus-symbolic", valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        self.plus_button = Gtk.Button(icon_name="plus-symbolic", valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)

        self.scale.connect("value-changed", self.on_scale_value_changed)
        self.minus_button.connect("clicked", self.on_minus_btn_clicked)
        self.plus_button.connect("clicked", self.on_plus_btn_clicked)

        self.add_suffix(self.minus_button)
        self.add_suffix(self.scale)
        self.add_suffix(self.plus_button)

    def set_range(self, value: float = None, lower: float = None, upper: float = None, step: float = None):
        adj = self.scale.get_adjustment()
        if value is None:
            value = self.scale.get_value()
        if lower is None:
            lower = adj.get_lower()
        if upper is None:
            upper = adj.get_upper()
        if step is None:
            step = adj.get_step_increment()
        self.scale.set_adjustment(Gtk.Adjustment(value=value, lower=lower, upper=upper, step_increment=step))

    def set_digits(self, num_digits: int = 0):
        self.scale.set_digits(num_digits)

    def get_value(self) -> float:
        return self.scale.get_value()

    def on_scale_value_changed(self, *args):
        val = self.scale.get_value()
        self.emit("value-changed", val)  # re-emit the signal

    def on_minus_btn_clicked(self, *args):
        val = self.scale.get_value()
        step_inc = self.scale.get_adjustment().get_step_increment()
        self.scale.set_value(val - step_inc)

    def on_plus_btn_clicked(self, *args):
        val = self.scale.get_value()
        step_inc = self.scale.get_adjustment().get_step_increment()
        self.scale.set_value(val + step_inc)


class AdditionalContentRow(PrefRow):
    __gtype_name__ = "AdditionalContentRow"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.box = self.header_box

        # temporarely remove existing widgets
        self.box.remove(self.prefixes_box)
        self.box.remove(self.header_image)
        self.box.remove(self.title_box)
        self.box.remove(self.suffixes_box)

        # restyle the header
        self.box.set_properties(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            margin_top=8,
            margin_bottom=8,
        )

        # create new containers
        self.header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, visible=False)

        # add previous widgets (from the AdwActionRow) to new header
        self.header_box.append(self.prefixes_box)
        self.header_box.append(self.header_image)
        self.header_box.append(self.title_box)
        self.header_box.append(self.suffixes_box)

        # if content is not None:
        #     self.content_box.append(content)
        # self.footer.append()

        # add all new containers to the header
        self.box.append(self.header_box)
        self.box.append(self.content_box)
        self.box.append(self.footer_box)

        self.title_lbl.connect("notify::label", self._on_title_changed)
        self.subtitle_lbl.connect("notify::label", self._on_subtitle_changed)

        # manually invoke to check if title/subtitle dont exist
        self._on_title_changed()

    def _on_title_changed(self, *args):
        if not self.title_lbl.get_label():
            if not self.subtitle_lbl.get_label():
                self.header_box.set_visible(False)
            else:
                self.title_lbl.set_visible(False)
        else:
            self.title_lbl.set_visible(True)

    def _on_subtitle_changed(self, *args):
        if not self.subtitle_lbl.get_label():
            if not self.title_lbl.get_label():
                self.header_box.set_visible(False)
            else:
                self.subtitle_lbl.set_visible(False)
        else:
            self.subtitle_lbl.set_visible(True)

    def add_footer_widget(self, widget: Gtk.Widget, prepend: bool = False) -> Gtk.Widget:
        if prepend:
            self.footer_box.prepend(widget)
        else:
            self.footer_box.append(widget)
        self.footer_box.set_visible(True)
        return widget

    def add_footer_btn(
        self,
        *,
        label: str = "",
        icon_name: str = "",
        func: Callable,
        func_kwargs: dict = {},
        prepend: bool = False,
        css_classes: list[str] = [],
        **kwargs,
    ) -> Gtk.Button:
        btn = Gtk.Button(child=Adw.ButtonContent(label=label, icon_name=icon_name), **kwargs)
        btn.connect("clicked", lambda *_: func(**func_kwargs))
        for css_class in css_classes:
            btn.add_css_class(css_class)
        return self.add_footer_widget(btn, prepend=prepend)


class TextViewRow(AdditionalContentRow):
    __gtype_name__ = "TextViewRow"

    def __init__(
        self,
        *,
        text: str = "",
        min_height: int = -1,
        max_height: int = -1,
        editable: bool = True,
        show_copy_btn: bool = True,
        wrap_mode: Gtk.WrapMode = Gtk.WrapMode.WORD_CHAR,
        **kwargs,
    ):
        super().__init__(**kwargs)
        # self.filterable = False

        self.min_height = min_height
        self.max_height = max_height
        self.frame: Gtk.Frame = Gtk.Frame(hexpand=True, vexpand=True)
        self.scroll: Gtk.ScrolledWindow = Gtk.ScrolledWindow(propagate_natural_height=True)
        self.frame.set_child(self.scroll)
        self.content_box.append(self.frame)

        self.text_view = Gtk.TextView(
            wrap_mode=wrap_mode,
            cursor_visible=editable,
            editable=editable,
            monospace=True,
            vexpand=True,
            left_margin=12,
            right_margin=12,
            top_margin=12,
            bottom_margin=12,
        )
        self.scroll.set_child(self.text_view)
        self.text_buffer = self.text_view.get_buffer()
        self.text_buffer.connect("changed", self.on_text_changed)

        # copy button
        self.copy_btn = self.add_suffix(
            CopyButton(
                copy_callback=self.get_text,
                tooltip_text="Copy text",
                visible=show_copy_btn,
            )
        )

    @property
    def line_count(self) -> int:
        return self.text_buffer.get_line_count()

    @property
    def filter_text(self) -> str:
        return f"{self.title_lbl.get_text()} {self.subtitle_lbl.get_text()} {self.get_text()}"

    def on_text_changed(self, *args):
        # TODO add that tabs are replaced by spaces
        GLib.idle_add(self.update_height)

    def set_title(self, title: str):
        self.title_lbl.set_label(str(title))
        self.title_lbl.set_visible(len(str(title)) > 0)
        self.header_box.set_visible(len(self.title_lbl.get_label()) > 0 or len(self.subtitle_lbl.get_label()) > 0)

    def set_subtitle(self, subtitle: str):
        self.subtitle_lbl.set_label(str(subtitle))
        self.subtitle_lbl.set_visible(len(str(subtitle)) > 0)
        self.header_box.set_visible(len(self.title_lbl.get_label()) > 0 or len(self.subtitle_lbl.get_label()) > 0)

    def get_text(self) -> str:
        start_iter = self.text_buffer.get_start_iter()
        end_iter = self.text_buffer.get_end_iter()
        return self.text_buffer.get_text(start_iter, end_iter, True)

    def set_text(self, text: str):
        self.text_buffer.set_text(str(text).rstrip())

    def append_text(self, text: str):
        self.text_buffer.insert(self.text_buffer.get_end_iter(), str(text))

    def append_tagged_text(self, text: str, tag: str):
        # self.add_tag(tag) # TODO
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), str(text), str(tag))

    def prepend_text(self, text: str):
        self.text_buffer.insert(self.text_buffer.get_start_iter(), str(text))

    def prepend_tagged_text(self, text: str, tag: str):
        # self.add_tag(tag) # TODO
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

    def update_height(self):
        natural_height = self.text_view.get_preferred_size().natural_size.height
        if self.min_height != -1:
            self.scroll.set_min_content_height(self.min_height)
        else:
            if self.max_height == -1:
                updated_height = natural_height
            else:
                updated_height = min(self.max_height, natural_height)
            self.scroll.set_min_content_height(updated_height)

        return False

    # TODO do the filtering with GtkTextTags
    def filter_by_text(self, filter_snippets: list[str]):
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

    # TODO not really working
    def filter_by_tags(self, tag_names: list[str]):
        tag_table = self.text_buffer.get_tag_table()
        tag_table.foreach(lambda tag: print(tag.get_property("name")))

        def toggle_tag_visibility(tag):
            if tag.get_property("name") not in tag_names:
                tag.set_property("invisible", True)
            else:
                tag.set_property("invisible", False)

        tag_table.foreach(lambda tag: toggle_tag_visibility(tag))


class ImageViewRow(AdditionalContentRow):
    __gtype_name__ = "ImageViewRow"

    def __init__(self, *, image: Gtk.Picture = None, max_height: int = 200, **kwargs):
        super().__init__(**kwargs)
        # self.filterable = False

        self.max_height = max_height
        self.image: Gtk.Picture = image
        self.frame: Gtk.Frame = Gtk.Frame(hexpand=True, vexpand=True)
        self.content_box.append(self.frame)

        if image is None:
            self.reset_image_to_default_icon()
            # self.footer_box.set_sensitive(False) # TODO
        else:
            self.frame.set_child(self.image)

        # fill footer with buttons
        self.zoom_in_btn = self.add_footer_btn(
            label="",
            icon_name="zoom-in-symbolic",
            tooltip_text="Zoom in",
            func=self.on_zoom_in,
        )
        self.zoom_out_btn = self.add_footer_btn(
            label="",
            icon_name="zoom-out-symbolic",
            tooltip_text="Zoom out",
            func=self.on_zoom_out,
        )
        self.fit_to_width_btn = self.add_footer_btn(
            label="",
            icon_name="zoom-fit-best-symbolic",
            tooltip_text="Fit to width",
            func=self.on_fit_to_width,
        )
        self.copy_img_btn = self.add_footer_btn(
            label="Copy",
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy image",
            func=self.on_copy_image,
        )
        self.open_img_btn = self.add_footer_btn(
            label="Open",
            icon_name="folder-open-symbolic",
            tooltip_text="Open image",
            func=self.on_open_image,
        )
        self.save_img_btn = self.add_footer_btn(
            label="Save",
            icon_name="document-save-symbolic",
            tooltip_text="Save image",
            func=self.on_save_image,
            css_classes=["suggested-action"],
            hexpand=True,
        )
        self.footer_box.set_visible(True)

        self.current_texture = None  # Track the last texture
        self.pending_frame = None  # Store the next frame to be displayed
        self.updating = False  # Prevent redundant updates

    def reset_image_to_default_icon(self, tooltip_text: str = "No image"):
        self.set_image_from_icon_name(icon_name="dialog-error-symbolic", tooltip_text=tooltip_text)

    def set_image_from_icon_name(self, *, icon_name: str, tooltip_text: str = "", size: int = 100):
        display = Gdk.Display.get_default()
        if not display:
            return  # In case there's no display available

        size = max(10, min(size, self.max_height))
        icon_theme = Gtk.IconTheme.get_for_display(display)
        icon_paintable = icon_theme.lookup_icon(
            icon_name,
            ["dialog-error-symbolic"],  # fallbacks
            size,  # size
            1,  # scale
            Gtk.TextDirection.NONE,
            Gtk.IconLookupFlags.PRELOAD,
        )
        if icon_paintable:
            self.icon_image: Gtk.Picture = Gtk.Picture(
                paintable=icon_paintable,
                tooltip_text=tooltip_text,
                margin_top=12,
                margin_bottom=12,
                margin_start=12,
                margin_end=12,
                # width_request=size,
                # height_request=size,
            )
            self.frame.set_child(self.icon_image)
            self.frame.set_size_request(width=size, height=size)

    def set_image_from_opencv(self, cv_image):
        if cv_image is None:
            raise RuntimeError("Image has no data")

        new_image = Gtk.Picture()

        # TODO also check for other datatypes
        # If necessary, convert BGR -> RGB (depends on your data format).
        # cv_image is shape (height, width, channels).
        cv_image_rgb = cv_image[:, :, ::-1] if cv_image.shape[-1] == 3 else cv_image
        height, width, channels = cv_image_rgb.shape
        rowstride = width * 3  # 3 bytes per pixel (RGB)

        # resize the image accordingly
        natural_width = self.frame.get_allocated_width()
        scale_factor = natural_width / width
        new_height = int(height * scale_factor)
        self.frame.set_size_request(width=natural_width, height=new_height)

        # Convert the numpy image to bytes
        data = cv_image_rgb.tobytes()
        # Wrap the bytes in a GLib.Bytes object
        bytes_data = GLib.Bytes.new(data)

        # Create a MemoryTexture directly from the image data (RGB8).
        # Alternatively, for RGBA data, use Gdk.MemoryFormat.RGBA8, etc.
        new_texture = Gdk.MemoryTexture.new(width, height, Gdk.MemoryFormat.R8G8B8, bytes_data, rowstride)

        # Queue the frame for display
        self.pending_frame = new_texture

        # Thread-safe update of the widget's content on the GTK main loop.
        def _update_texture():
            if self.pending_frame:
                self.current_texture = self.pending_frame
                new_image.set_paintable(self.current_texture)
                self.image = new_image
                self.frame.set_child(self.image)
                self.pending_frame = None  # Clear the pending frame

            self.updating = False  # Allow new frames to be processed

        # Schedule widget update on the GTK main thread.
        # Schedule an update (ensuring it's only called once per GTK frame cycle)
        if not self.updating:
            self.updating = True
            GLib.idle_add(_update_texture)

    def on_save_image(self, *args):
        # TODO implement saving behaviour
        print("saving")
        pass

    def on_copy_image(self, *args):
        # TODO implement copying behaviour
        print("copying")
        pass

    def on_zoom_in(self, *args):
        # TODO implement zoom in
        print("zoom in")
        pass

    def on_zoom_out(self, *args):
        # TODO implement zoom out
        print("zoom out")
        pass

    def on_fit_to_width(self, *args):
        # TODO implement fit to width
        print("fit to width")
        pass

    def on_open_image(self, *args):
        # TODO implement open image
        print("open image")
        pass


class ColumnViewRow(AdditionalContentRow):
    __gtype_name__ = "ColumnViewRow"

    def __init__(self, row_object: GObject.GObject, **kwargs):
        super().__init__(**kwargs)
        super().set_activatable(False)
        # self.filterable = False

        self.column_view = Gtk.ColumnView(show_column_separators=True, show_row_separators=True)
        self.frame: Gtk.Frame = Gtk.Frame(hexpand=True, vexpand=True)
        self.scroll: Gtk.ScrolledWindow = Gtk.ScrolledWindow(
            propagate_natural_height=True, height_request=500
        )  # TODO make this configurable
        self.scroll.set_child(self.column_view)
        self.frame.set_child(self.scroll)
        self.content_box.append(self.frame)

        # Data Model for Log Messages
        self.row_object = row_object
        self.data_model = Gio.ListStore(item_type=row_object)

        # Filtering
        self.filter_conditions = {}
        self.filter = Gtk.CustomFilter.new(self._filter_func)
        self._filter_model = Gtk.FilterListModel(model=self.data_model, filter=self.filter)

        # Sorting model
        self.sorter_model = Gtk.SortListModel.new(model=self._filter_model, sorter=None)
        self._selection_model = Gtk.SingleSelection.new(model=self.sorter_model)
        self.column_view.set_model(self._selection_model)

        # Store column references
        self.columns = []
        # self._reset_model()

    def add_column(
        self,
        title: str,
        property_name: str,
        is_sortable: bool = True,
        is_numeric: bool = False,
        expand: bool = False,
    ):
        def _on_factory_setup(_factory, list_item):
            label = Gtk.Label(halign=Gtk.Align.START, margin_top=2, margin_bottom=2, selectable=True)
            list_item.set_child(label)

        def _on_factory_bind(_factory, list_item, property_name):
            label_widget = list_item.get_child()
            log_message = list_item.get_item()
            label_widget.set_label(str(getattr(log_message, property_name)))

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", _on_factory_setup)
        factory.connect("bind", _on_factory_bind, property_name)

        column = Gtk.ColumnViewColumn(title=title, factory=factory, expand=expand)
        self.columns.append(column)
        self.column_view.append_column(column)

        if is_sortable:
            prop_expr = Gtk.PropertyExpression.new(self.row_object, None, property_name)
            sorter = Gtk.NumericSorter.new(prop_expr) if is_numeric else Gtk.StringSorter.new(prop_expr)
            column.set_sorter(sorter)

    def change_header(self, column_index: int, new_title: str):
        if column_index < 0 or column_index >= len(self.columns):
            raise IndexError("Invalid column index.")

        self.columns[column_index].set_title(new_title)

    def get_headers(self) -> list[str]:
        return [column.get_title() for column in self.columns]

    def add_row(self, row_object: GObject.GObject) -> int:
        GLib.idle_add(self.data_model.append, row_object)

    # TODO make this a fuzzy search
    def _match_filter(self, string: str, pattern: str) -> bool:
        if pattern == "":
            return True

        try:
            if string is None or pattern is None:
                return False  # Avoid searching in None values

            match = re.search(pattern, string, re.IGNORECASE)

            if match is None or not match:
                return False  # No match found

            return True  # Match found
        except re.error:
            return True

    # TODO make this a fuzzy search
    def _filter_func(self, row_object: GObject.GObject):
        if not row_object or not self.filter_conditions:
            return True  # No filters applied, show all rows

        row_properties = {p.name: getattr(row_object, p.name) for p in row_object.list_properties()}

        for property_name, filter_value in self.filter_conditions.items():
            if property_name not in row_properties:
                continue  # Ignore non-existent properties

            cell_value = str(row_properties[property_name])

            if isinstance(filter_value, str):
                if not self._match_filter(cell_value, filter_value):
                    return False  # Exclude row if no match

            elif isinstance(filter_value, list):
                # At least one pattern in the list must match
                if not any(self._match_filter(cell_value, pattern) for pattern in filter_value):
                    return False  # Exclude row if none of the patterns match

        return True  # Show the row if it passes all filters

    def apply_filter(self, **filter_kwargs):
        """
        Applies column-specific filters using keyword arguments.

        Example usage:
            apply_filter(timestamp="2023", severity=["ERROR", "INFO"], message="System")

        - Filters apply to properties of the GObject.
        - A value can be:
            - `None`: No filtering for that property.
            - A `str`: The property must contain this substring.
            - A `list[str]`: The property must contain at least one of these substrings.
        - Properties not mentioned in `kwargs` will default to `None` (no filtering).
        """
        # Get all GObject properties and initialize missing ones with None
        self.filter_conditions.update(filter_kwargs)  # Store only provided filters
        self.filter.changed(Gtk.FilterChange.DIFFERENT)  # Refresh filtering

    def clear_rows(self):
        self.data_model.remove_all()


# somewhat based on
# https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.1/class.ButtonRow.html
class ButtonRow(Adw.PreferencesRow, PrefRowInterface):
    __gtype_name__ = "ButtonRow"

    def __init__(
        self,
        *,
        label: str = "",
        start_icon_name: str = "",
        end_icon_name: str = "",
        tooltip_text: str = "",
        func: Callable,
        func_kwargs: dict = {},
        btn_css_classes: list[str] = [],
        **kwargs,
    ):
        Adw.PreferencesRow.__init__(self, **kwargs)
        PrefRowInterface.__init__(self)
        super().set_activatable(False)

        self.btn = Gtk.Button(
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
            tooltip_text=tooltip_text,
        )
        self.btn.connect("clicked", lambda *_: func(**func_kwargs))

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.CENTER)
        self.start_icon = Gtk.Image(icon_name=start_icon_name)
        self.btn_label = Gtk.Label(label=label)
        self.end_icon = Gtk.Image(icon_name=end_icon_name)

        self.content_box.append(self.start_icon)
        self.content_box.append(self.btn_label)
        self.content_box.append(self.end_icon)

        self.btn.set_child(self.content_box)
        super().set_child(self.btn)

        for css_class in btn_css_classes:
            self.btn.add_css_class(css_class)

    @GObject.Property(type=str, default="")
    def filter_text(self) -> str:
        return self.btn_label.get_label().lower()


# TODO make the multibtn and mutlitogglebtn rows inherit from the multiwidget row
class MultiWidgetRow(Adw.PreferencesRow, PrefRowInterface):
    __gtype_name__ = "MultiWidgetRow"

    def __init__(self, **kwargs):
        Adw.PreferencesRow.__init__(self, **kwargs)
        PrefRowInterface.__init__(self)
        super().set_activatable(False)

        self.content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            halign=Gtk.Align.FILL,
            hexpand=True,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
            css_classes=["linked"],
            **kwargs,
        )
        super().set_child(self.content_box)
        self.widgets = []

    def add_widget(self, widget: Gtk.Widget, prepend: bool = False) -> Gtk.Widget:
        if prepend:
            self.content_box.prepend(widget)
        else:
            self.content_box.append(widget)

        self.widgets.append(widget)
        return widget

    def add_widgets(self, widgets: list[Gtk.Widget], prepend: bool = False):
        for widget in widgets:
            self.add_widget(widget, prepend=prepend)

        return self.widgets


class MultiBoxRow(Adw.PreferencesRow, PrefRowInterface):
    __gtype_name__ = "MultiBoxRow"

    def __init__(self, **kwargs):
        Adw.PreferencesRow.__init__(self, **kwargs)
        PrefRowInterface.__init__(self)
        super().set_activatable(False)

        self.content_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
            halign=Gtk.Align.FILL,
            hexpand=True,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
            css_classes=["linked"],
            **kwargs,
        )
        super().set_child(self.content_box)

        self.boxes = []

    def add_label_pair(self, title: str, subtitle: str, prop: bool = False, **kwargs) -> Gtk.Widget:
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            halign=Gtk.Align.FILL,
            hexpand=True,
            # margin_top=8,
            # margin_bottom=8,
            # margin_start=12,
            # margin_end=12,
            css_classes=["title"],
        )
        box.append(Gtk.Label(label=title, xalign=0.0, css_classes=["title"]))
        box.append(Gtk.Label(label=subtitle, xalign=0.0, css_classes=["subtitle"]))

        self.content_box.append(box)
        self.boxes.append(box)
        return box


class MultiButtonRow(Adw.PreferencesRow, PrefRowInterface):
    __gtype_name__ = "MultiButtonRow"

    def __init__(self, **kwargs):
        Adw.PreferencesRow.__init__(self, **kwargs)
        PrefRowInterface.__init__(self)
        super().set_activatable(False)

        self.content_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            homogeneous=True,
            spacing=0,
            halign=Gtk.Align.FILL,
            hexpand=True,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
            css_classes=["linked"],
            **kwargs,
        )
        super().set_child(self.content_box)

        self.buttons = []

    def add_button(self, btn: Gtk.Button, prepend: bool = False):
        if prepend:
            self.content_box.prepend(btn)
        else:
            self.content_box.append(btn)

        self.buttons.append(btn)
        return btn


class MultiToggleButtonRow(AdditionalContentRow):
    __gtype_name__ = "MultiToggleButtonRow"
    __gsignals__ = {"button-toggled": (GObject.SignalFlags.RUN_FIRST, None, (str, bool))}

    def __init__(self, show_quickselect_btns: bool = False, **kwargs):
        super().__init__(**kwargs)
        super().set_activatable(False)

        self.content_box.set_properties(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=0,
            halign=Gtk.Align.FILL,
            hexpand=True,
            css_classes=["linked"],
        )

        self.activate_all_btn = self.add_suffix_btn(
            icon_name="check-round-outline-symbolic",
            tooltip_text="Activate all",
            func=self.toggle_all,
            func_kwargs={"active": True},
        )
        self.deactivate_all_btn = self.add_suffix_btn(
            icon_name="cross-small-circle-outline-symbolic",
            tooltip_text="Deactivate all",
            func=self.toggle_all,
            func_kwargs={"active": False},
        )
        self.suffixes_box.add_css_class("linked")

        self.buttons = {}

    def add_toggle_btn(self, unique_id: str | int, **kwargs):
        if not unique_id:
            raise ValueError("unique_id for ToggleButton must not be empty")
        for btn_id in self.buttons.keys():
            if btn_id == unique_id:
                raise ValueError(f"ToggleButton with unique_id '{unique_id}' already exists, but they must be unique")

        toggle_btn = ToggleButton(func=self.on_btn_toggled, hexpand=True, halign=Gtk.Align.FILL, **kwargs)
        # toggle_btn.connect("toggled", self.on_btn_toggled)
        self.content_box.append(toggle_btn)
        self.buttons[unique_id] = toggle_btn
        return toggle_btn

    def get_active_buttons(self) -> dict:
        return {btn_id: btn for btn_id, btn in self.buttons.items() if btn.get_active()}

    def get_button_id(self, btn: ToggleButton) -> int | str:
        for _id, b in self.buttons.items():
            if b == btn:
                return _id
        else:
            raise ValueError("Button not found")

    def get_all_btn_states(self) -> dict:
        return {btn_id: (btn, btn.get_active()) for btn_id, btn in self.buttons.items()}

    def on_btn_toggled(self, btn: ToggleButton, is_active: bool, *args):
        _id = self.get_button_id(btn)
        super().emit("button-toggled", _id, is_active)

    def toggle_all(self, active: bool):
        for btn in self.buttons.values():
            btn.set_active(active)


# TODO this is not really tested yet
class SearchRow(Adw.PreferencesRow, PrefRowInterface):
    __gtype_name__ = "SearchRow"

    # box: Gtk.Box = Gtk.Template.Child()
    # start_icon: Gtk.Image = Gtk.Template.Child()
    # search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    # end_icon: Gtk.Image = Gtk.Template.Child()

    def __init__(
        self,
        *,
        title: str = "",
        start_icon_name: str = "go-prev-symbolic",
        end_icon_name: str = "go-next-symbolic",
        # tooltip_text: str = "",
        placeholder_text: str = "",
        search_func: Callable = None,
        search_kwargs: dict = {},
        css_classes: list[str] = [],
        **kwargs,
    ):
        Adw.PreferencesRow.__init__(self, **kwargs)
        PrefRowInterface.__init__(self)
        super().set_activatable(False)
        # super().get_first_child().get_first_child().get_next_sibling().get_next_sibling().set_visible(False)
        # PrefRow -> header -> prefixes -> image -> title_box
        # super().set_activatable_widget(self.btn)

        self.content_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            valign=Gtk.Align.FILL,
            hexpand=True,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
        )
        self.start_icon = Gtk.Image(icon_name=start_icon_name, halign=Gtk.Align.START, visible=False)
        self.content_box.append(self.start_icon)

        self.search_entry = Gtk.SearchEntry(
            placeholder_text=placeholder_text,
            search_delay=100,
            halign=Gtk.Align.FILL,
            valign=Gtk.Align.CENTER,
            hexpand=True,
        )
        self.search_entry.connect("search-changed", self.on_search_entry_changed)
        self.content_box.append(self.search_entry)

        self.end_icon = Gtk.Image(icon_name=end_icon_name, halign=Gtk.Align.END, visible=False)
        self.content_box.append(self.end_icon)

        super().set_child(self.content_box)

        # if title:
        #     self.btn.set_label(str(title))

        if start_icon_name:
            self.start_icon.set_from_icon_name(start_icon_name)
            self.start_icon.set_visible(True)

        if end_icon_name:
            self.end_icon.set_from_icon_name(end_icon_name)
            self.end_icon.set_visible(True)

        # if tooltip_text:
        #     self.btn.set_tooltip_text(tooltip_text)

        # if placeholder_text:
        #     self.search_entry.set_placeholder_text(placeholder_text)

        if search_func:
            self.search_func = search_func
        else:
            self.search_func = lambda x: print("no search func specified")

        for css_class in css_classes:
            super().add_css_class(css_class)

    @property
    def filter_text(self) -> str:
        return ""

    def on_search_entry_changed(self, *args):
        self.search_func(self.search_entry.get_text())


class SuggestionEntryRow(Adw.EntryRow, PrefRowInterface):
    __gtype_name__ = "SuggestionEntryRow"
    __gsignals__ = {"suggestion-apply": (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self, *, title: str = "Select or create…", **kwargs):
        Adw.EntryRow.__init__(self, **kwargs)
        PrefRowInterface.__init__(self)
        super().set_title(title)
        super().set_show_apply_button(True)
        self.connect("apply", self.on_apply)

        # Suffix button to open popover
        self.popover = Gtk.Popover(position=Gtk.PositionType.BOTTOM, autohide=True)
        self.popover_btn = Gtk.MenuButton(
            always_show_arrow=True,
            tooltip_text="Show suggestions",
            direction=Gtk.ArrowType.DOWN,
            popover=self.popover,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        self.add_suffix(self.popover_btn)

        # Container inside popover
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # SearchEntry to filter items
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Filter…")
        self.search_entry.connect("search-changed", self.on_search_changed)
        popover_box.append(self.search_entry)

        # wrap in FilterListModel with CustomFilter to always include 'new'
        self.list_store = Gio.ListStore.new(Gtk.StringObject)
        self._filter_model = Gtk.CustomFilter.new(self.filter_func)
        self._selection_model = Gtk.SingleSelection(
            model=Gtk.FilterListModel(model=self.list_store, filter=self._filter_model),
            autoselect=False,
            # can_unselect=True,
        )
        self._selection_model.connect("notify::selected-item", self.on_selected_item_changed)

        def _on_factory_setup(factory, list_item):
            lbl = Gtk.Label(
                xalign=0,
                ellipsize=Pango.EllipsizeMode.MIDDLE,
                max_width_chars=50,
                margin_top=8,
                margin_start=8,
                margin_bottom=8,
                margin_end=8,
            )
            list_item.set_child(lbl)

        def _on_factory_bind(factory, list_item):
            lbl = list_item.get_child()
            itm = list_item.get_item()
            item_text = itm.get_string()
            lbl.set_text(item_text)
            lbl.set_tooltip_text(item_text)

        # ListItemFactory for rendering
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", _on_factory_setup)
        factory.connect("bind", _on_factory_bind)

        self._list_view = Gtk.ListView(model=self._selection_model, factory=factory)
        scrolled_window = Gtk.ScrolledWindow(max_content_height=300, propagate_natural_height=True)
        scrolled_window.set_child(self._list_view)
        popover_box.append(scrolled_window)
        self.popover.set_child(popover_box)
        self.popover.set_default_widget(self.search_entry)

    def filter_func(self, item) -> bool:
        # Case-insensitive substring search
        query = self.search_entry.get_text().lower()
        return query in item.get_string().lower()

    def on_search_changed(self, *args):
        # Notify filter to reevaluate
        self._filter_model.changed(Gtk.FilterChange.DIFFERENT)

    def on_selected_item_changed(self, selection, pspec):
        if not self.popover_btn.get_active():
            return

        # Called when user picks an item
        selected = selection.get_selected_item()
        if selected:
            item_text = selected.get_string()
            self.set_text(item_text)
            self.popover.popdown()
            # self._selection_model.set_selected(Gtk.INVALID_LIST_POSITION)
            self.emit("suggestion-apply", item_text)

    def on_apply(self, *args):
        # When user edits text, clear any existing selection in the list
        self._selection_model.set_selected(Gtk.INVALID_LIST_POSITION)
