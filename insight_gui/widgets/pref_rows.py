from typing import Callable
import re  # regex

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GObject, Gtk, Adw, Gdk, GLib

from insight_gui.widgets.buttons import CopyButton


class GenericRow(GObject.GObject):
    """Abstract Base Class for common row properties."""

    __gtype_name__ = "GenericRow"

    def __init__(self):
        super().__init__()
        self._filter_text = ""

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


class PrefRow(Adw.ActionRow, GenericRow):
    __gtype_name__ = "PrefRow"

    def __init__(
        self,
        *,
        title: str = "",
        subtitle: str = "",
        css_classes: list[str] = [],
        **kwargs,
    ):
        Adw.ActionRow.__init__(self, **kwargs)
        GenericRow.__init__(self)
        super().set_use_markup(False)

        self.header_box: Gtk.Box = self.get_first_child()
        self.prefixes_box: Gtk.Box = self.header_box.get_first_child()
        self.header_image: Gtk.Image = self.prefixes_box.get_next_sibling()
        self.title_box: Gtk.Box = self.header_image.get_next_sibling()
        self.suffixes_box: Gtk.Image = self.title_box.get_next_sibling()

        # self.prefixes_box.set_visible(False)
        # self.suffixes_box.set_visible(False)

        self.title_lbl: Gtk.Label = self.title_box.get_first_child()
        self.subtitle_lbl: Gtk.Label = self.title_lbl.get_next_sibling()

        # react to hide header
        if not title and not subtitle:
            self.title_box.set_visible(False)
        super().set_title(str(title))
        super().set_subtitle(str(subtitle))

        for css_class in css_classes:
            super().add_css_class(css_class)

        self.next_page_icon: Gtk.Image = Gtk.Image(icon_name="go-next-symbolic", visible=False)
        self.add_suffix(self.next_page_icon)

    @GObject.Property(type=str, default="")
    def filter_text(self) -> str:
        return f"{super().get_title()} {super().get_subtitle()}".lower()

    def add_prefix(self, widget: Gtk.Widget, *, prepend: bool = False):
        if prepend:
            self.prefixes_box.prepend(widget)
        else:
            self.prefixes_box.append(widget)
        self.prefixes_box.set_visible(True)
        return widget

    def add_prefix_lbl(self, label: str, *, prepend: bool = False, **kwargs):
        return self.add_prefix(Gtk.Label(label=label, **kwargs), prepend=prepend)

    def add_prefix_icon(self, icon_name: str, *, tooltip_text: str = "", prepend: bool = False, **kwargs):
        return self.add_prefix(Gtk.Image(icon_name=icon_name, tooltip_text=tooltip_text, **kwargs), prepend=prepend)

    def add_prefix_btn(
        self,
        *,
        icon_name: str,
        func: Callable,
        func_kwargs: dict = {},
        tooltip_text: str = "",
        prepend: bool = False,
        **kwargs,
    ):
        btn = Gtk.Button(
            icon_name=icon_name, tooltip_text=tooltip_text, vexpand=False, valign=Gtk.Align.CENTER, **kwargs
        )
        btn.connect("clicked", lambda *_: func(**func_kwargs))
        return self.add_prefix(btn, prepend=prepend)

    def add_suffix(self, widget: Gtk.Widget, *, prepend: bool = False):
        if prepend:
            self.suffixes_box.prepend(widget)
        else:
            self.suffixes_box.append(widget)
            self.suffixes_box.reorder_child_after(self.next_page_icon, widget)

        self.suffixes_box.set_visible(True)
        return widget

    def add_suffix_lbl(self, label: str, *, prepend: bool = False, **kwargs):
        return self.add_suffix(Gtk.Label(label=label, **kwargs), prepend=prepend)

    def add_suffix_icon(self, icon_name: str, *, tooltip_text: str = "", prepend: bool = False, **kwargs):
        return self.add_suffix(Gtk.Image(icon_name=icon_name, tooltip_text=tooltip_text, **kwargs), prepend=prepend)

    def add_suffix_btn(
        self,
        *,
        icon_name: str,
        func: Callable,
        func_kwargs: dict = {},
        tooltip_text: str = "",
        prepend: bool = False,
        **kwargs,
    ):
        btn = Gtk.Button(
            icon_name=icon_name, tooltip_text=tooltip_text, vexpand=False, valign=Gtk.Align.CENTER, **kwargs
        )
        btn.connect("clicked", lambda *_: func(**func_kwargs))
        return self.add_suffix(btn, prepend=prepend)

    def set_subpage_link(
        self, *, nav_view: Adw.NavigationView, subpage_class: type[Adw.NavigationPage], **subpage_kwargs
    ):
        def _on_activate(*args):
            nav_view.push(subpage_class(nav_view=nav_view, **subpage_kwargs))

        if hasattr(self, "subpage_signal_handler"):
            super().disconnect(self.subpage_signal_handler)

        self.subpage_signal_handler = super().connect("activated", _on_activate)
        super().set_activatable(True)
        self.next_page_icon.set_visible(True)


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
        self.box.set_orientation(Gtk.Orientation.VERTICAL)
        self.box.set_spacing(6)
        self.box.set_margin_top(8)
        self.box.set_margin_bottom(8)

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

    def add_footer_widget(self, widget: Gtk.Widget, prepend: bool = False):
        if prepend:
            self.footer_box.prepend(widget)
        else:
            self.footer_box.append(widget)
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
    ):
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
        max_height: int = 200,
        editable: bool = True,
        show_copy_btn: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.max_height = max_height
        self.frame: Gtk.Frame = Gtk.Frame(hexpand=True, vexpand=True)
        self.scroll: Gtk.ScrolledWindow = Gtk.ScrolledWindow(propagate_natural_height=True)
        self.frame.set_child(self.scroll)
        self.content_box.append(self.frame)

        self.text_view = Gtk.TextView(
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
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
        if self.max_height == -1:
            updated_height = natural_height
        else:
            updated_height = min(self.max_height, natural_height)
        self.scroll.set_min_content_height(updated_height)

    # TODO do the filtering with GtkTextTags
    def filter(self, filter_snippets: list[str]):
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

        self.max_height = max_height
        self.image: Gtk.Picture = image
        self.frame: Gtk.Frame = Gtk.Frame(hexpand=True, vexpand=True)
        self.content_box.append(self.frame)

        if image is None:
            self.set_image_from_icon_name(icon_name="dialog-error-symbolic", tooltip_text="No image available")
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

    def set_image_from_icon_name(self, *, icon_name: str, tooltip_text: str = "", size: int = 100):
        display = Gdk.Display.get_default()
        if not display:
            return  # In case there's no display available

        icon_theme = Gtk.IconTheme.get_for_display(display)
        icon_paintable = icon_theme.lookup_icon(
            icon_name,
            ["dialog-error-symbolic"],  # fallbacks
            max(size, self.max_height),  # size
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
                width_request=100,
                height_request=100,
            )
            self.frame.set_child(self.icon_image)

    def set_image_from_opencv(self, cv_image):
        # TODO also check for other datatypes
        # If necessary, convert BGR -> RGB (depends on your data format).
        # cv_image is shape (height, width, channels).
        cv_image_rgb = cv_image[:, :, ::-1]
        height, width, channels = cv_image_rgb.shape
        rowstride = channels * width

        # resize the image accordingly
        natural_width = self.image.get_allocated_width()
        scale_factor = natural_width / width
        new_height = int(height * scale_factor)
        self.image.set_size_request(width=natural_width, height=new_height)

        # Convert the numpy image to bytes
        data = cv_image_rgb.tobytes()
        # Wrap the bytes in a GLib.Bytes object
        bytes_data = GLib.Bytes.new(data)

        # Create a MemoryTexture directly from the image data (RGB8).
        # Alternatively, for RGBA data, use Gdk.MemoryFormat.RGBA8, etc.
        self.texture = Gdk.MemoryTexture.new(width, height, Gdk.MemoryFormat.R8G8B8, bytes_data, rowstride)

        # Thread-safe update of the widget's content on the GTK main loop.
        def update_texture(texture: Gdk.Texture):
            self.image.set_paintable(texture)
            return False  # Returning False removes the idle callback

        # Schedule widget update on the GTK main thread.
        GLib.idle_add(update_texture, self.texture)

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


# somewhat based on
# https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.1/class.ButtonRow.html
class ButtonRow(Adw.PreferencesRow, GenericRow):
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
        GenericRow.__init__(self)
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


# TODO this is not really tested yet
class SearchRow(Adw.PreferencesRow, GenericRow):
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
        GenericRow.__init__(self)
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


# TODO add an entry row?
