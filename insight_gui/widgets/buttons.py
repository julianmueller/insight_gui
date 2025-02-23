from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class PlayPauseButton(Gtk.Button):
    __gtype_name__ = "PlayPauseButton"

    def __init__(
        self,
        *,
        func: Callable,
        func_kwargs: dict = {},
        default_play: bool = False,
        play_label: str = "",
        pause_label: str = "",
        play_tooltip: str = "",
        pause_tooltip: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.func = func
        self.func_kwargs = func_kwargs
        self.playing = default_play
        self.play_label = play_label
        self.pause_label = pause_label
        self.play_tooltip = play_tooltip
        self.pause_tooltip = pause_tooltip
        self.play_icon_name = "media-playback-start-symbolic"
        self.pause_icon_name = "media-playback-pause-symbolic"

        self.btn_content = Adw.ButtonContent()
        self.set_child(self.btn_content)

        if not pause_label:
            self.pause_label = self.play_label

        if not pause_tooltip:
            self.pause_tooltip = self.play_tooltip

        super().connect("clicked", self._on_clicked)
        self._update_btn_state()

    def _on_clicked(self, button):
        self.func(playing=self.playing, **self.func_kwargs)
        self._update_btn_state()

    @property
    def is_playing(self):
        return self.playing

    def _update_btn_state(self):
        if self.playing:
            self.btn_content.set_label(self.pause_label)
            self.btn_content.set_icon_name(self.pause_icon_name)
            super().set_tooltip_text(self.play_tooltip)
            self.playing = False
        else:
            self.btn_content.set_label(self.play_label)
            self.btn_content.set_icon_name(self.play_icon_name)
            super().set_tooltip_text(self.pause_tooltip)
            self.playing = True


# TODO this is just copy/past of the one above, adapt it for toggle functionality
# class PlayPauseToggleButton(Gtk.ToggleButton):
#     __gtype_name__ = "PlayPauseToggleButton"


class CopyButton(Gtk.Button):
    __gtype_name__ = "CopyButton"

    def __init__(
        self,
        copy_text: str = "",
        copy_callback: Callable = None,
        tooltip_text: str = "Copy to clipboard",
        toast_host: Gtk.Widget = None,
        **kwargs,
    ):
        super().__init__(
            icon_name="edit-copy-symbolic", tooltip_text=tooltip_text, vexpand=False, valign=Gtk.Align.CENTER, **kwargs
        )
        self.copy_text = copy_text
        self.copy_callback = copy_callback
        self.toast_host = toast_host
        self.connect("clicked", self.on_copy_button_clicked)

    def on_copy_button_clicked(self, *args):
        if self.copy_callback:
            self.copy_text = self.copy_callback()

        clip = super().get_clipboard()
        clip.set(str(self.copy_text))

        if self.toast_host:
            self.toast_host.add_toast(Adw.Toast(title=f"Copied '{self.copy_text}' to clipboard"))
