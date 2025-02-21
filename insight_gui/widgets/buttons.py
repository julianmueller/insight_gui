from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class PlayPauseButton(Gtk.Button):
    def __init__(
        self, callback: Callable, default_play: bool = False, play_tooltip: str = "", pause_tooltip: str = "", **kwargs
    ):
        super().__init__(**kwargs)
        self.callback = callback
        self.playing = default_play
        self.play_tooltip = play_tooltip
        self.pause_tooltip = pause_tooltip

        self.play_icon_name = "media-playback-start-symbolic"
        self.pause_icon_name = "media-playback-pause-symbolic"

        super().connect("clicked", self._on_clicked)
        self.toggle_btn_state()

    def _on_clicked(self, button):
        self.toggle_btn_state()
        self.callback(self.playing)

    @property
    def is_playing(self):
        return self.playing

    def toggle_btn_state(self):
        if self.playing:
            self.set_icon_name(self.pause_icon_name)
            super().set_tooltip_text(self.play_tooltip)
            self.playing = False
        else:
            self.set_icon_name(self.play_icon_name)
            super().set_tooltip_text(self.pause_tooltip)
            self.playing = True
