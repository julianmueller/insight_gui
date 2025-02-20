from pathlib import Path
import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk


@Gtk.Template(filename=str(Path(__file__).with_suffix(".ui")))
class ImageViewRow(Adw.PreferencesRow):
    __gtype_name__ = "ImageViewRow"

    main_box: Gtk.Box = Gtk.Template.Child()
    header_box: Gtk.Box = Gtk.Template.Child()
    title_label: Gtk.Label = Gtk.Template.Child()
    subtitle_label: Gtk.Label = Gtk.Template.Child()
    save_btn: Gtk.Button = Gtk.Template.Child()

    frame: Gtk.Frame = Gtk.Template.Child()
    picture: Gtk.Picture = Gtk.Template.Child()

    def __init__(
        self,
        *,
        title: str = "",
        subtitle: str = "",
        default_icon: str = "dialog-error-symbolic",
        max_height: int = 200,
        show_save_btn: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_height = max_height

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

        self.toggle_save_btn_visibility(show_save_btn)

        if default_icon:
            display = Gdk.Display.get_default()
            if not display:
                return  # In case there's no display available

            icon_theme = Gtk.IconTheme.get_for_display(display)
            icon_paintable = icon_theme.lookup_icon(
                default_icon,
                None,  # fallbacks
                100,  # size
                1,  # scale
                Gtk.TextDirection.NONE,
                Gtk.IconLookupFlags.PRELOAD,
            )
            if icon_paintable:
                # self.picture.set_margin_top(12)
                # self.picture.set_margin_bottom(12)
                # self.picture.set_margin_start(12)
                # self.picture.set_margin_end(12)
                # self.picture.set_size_request(width=100, height=100)
                self.picture.set_paintable(icon_paintable)

        # TODO add control buttons for the image:
        # - save image
        # - zoom / fit to width / open in popup?
        # - magnifying glass?
        # - view in image system image viewer
        # - pause the image stream

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

    def set_picture_from_opencv(self, cv_image):
        # TODO also check for other datatypes
        # If necessary, convert BGR -> RGB (depends on your data format).
        # cv_image is shape (height, width, channels).
        cv_image_rgb = cv_image[:, :, ::-1]
        height, width, channels = cv_image_rgb.shape
        rowstride = channels * width

        # resize the image accordingly
        natural_width = self.picture.get_allocated_width()
        scale_factor = natural_width / width
        new_height = int(height * scale_factor)
        self.picture.set_size_request(width=natural_width, height=new_height)

        # Convert the numpy image to bytes
        data = cv_image_rgb.tobytes()
        # Wrap the bytes in a GLib.Bytes object
        bytes_data = GLib.Bytes.new(data)

        # Create a MemoryTexture directly from the image data (RGB8).
        # Alternatively, for RGBA data, use Gdk.MemoryFormat.RGBA8, etc.
        self.texture = Gdk.MemoryTexture.new(width, height, Gdk.MemoryFormat.R8G8B8, bytes_data, rowstride)

        # Thread-safe update of the widget's content on the GTK main loop.
        def update_texture(texture: Gdk.Texture):
            self.picture.set_paintable(texture)
            return False  # Returning False removes the idle callback

        # Schedule widget update on the GTK main thread.
        GLib.idle_add(update_texture, self.texture)

    def toggle_save_btn_visibility(self, visible: bool):
        self.save_btn.set_visible(visible)

    @Gtk.Template.Callback()
    def on_save_btn_clicked(self, btn):
        # TODO implement saving behaviour
        pass
