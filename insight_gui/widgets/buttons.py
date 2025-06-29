# =============================================================================
# buttons.py
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

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GObject, Gtk, Adw


class ToggleButton(Gtk.ToggleButton):
    __gtype_name__ = "MyToggleButton"

    def __init__(
        self,
        func: Callable,
        func_kwargs: dict = {},
        default_active: bool = False,
        labels: tuple[str, str] | str = None,
        show_default_icons: bool = True,
        icon_names: tuple[str, str] | str = None,
        tooltip_texts: tuple[str, str] | str = None,
        css_classes: tuple[list[str], list[str]] | list[str] = None,
        # vexpand=False,
        # valign=Gtk.Align.CENTER,
        # hexpand=False,
        # halign=Gtk.Align.CENTER,
        **kwargs,
    ):
        super().__init__(
            active=default_active,
            **kwargs,
        )

        self.btn_content = Adw.ButtonContent()
        super().set_child(self.btn_content)

        if isinstance(icon_names, tuple):
            self.icon_names = icon_names
        elif isinstance(icon_names, str):
            self.icon_names = (icon_names, icon_names)
        else:
            self.icon_names = None

        if isinstance(labels, tuple):
            self.labels = labels
        elif isinstance(labels, str):
            self.labels = (labels, labels)
        else:
            self.labels = None

        if isinstance(tooltip_texts, tuple):
            self.tooltip_texts = tooltip_texts
        elif isinstance(tooltip_texts, str):
            self.tooltip_texts = (tooltip_texts, tooltip_texts)
        else:
            self.tooltip_texts = None

        if isinstance(css_classes, tuple):
            self.css_classes = css_classes
        elif isinstance(css_classes, list):
            self.css_classes = (css_classes, css_classes)
        else:
            self.css_classes = None

        if show_default_icons and self.icon_names is None:
            self.icon_names = ("check-round-outline-symbolic", "cross-small-circle-outline-symbolic")

        self.func = func
        self.func_kwargs = func_kwargs
        super().connect("toggled", self._on_toggle)
        self.update_button()

    @property
    def is_active(self) -> bool:
        return super().get_active()

    def _on_toggle(self, *args):
        self.func(self, self.is_active, **self.func_kwargs)
        self.update_button()

    def update_button(self):
        # Update icon if a tuple was provided
        if self.icon_names:
            self.btn_content.set_icon_name(self.icon_names[0] if self.is_active else self.icon_names[1])

        # Update label if a tuple was provided
        if self.labels:
            self.btn_content.set_label(self.labels[0] if self.is_active else self.labels[1])

        # Update tooltip if a tuple was provided
        if self.tooltip_texts:
            self.btn_content.set_tooltip_text(self.tooltip_texts[0] if self.is_active else self.tooltip_texts[1])

        # Update css classes if a tuple was provided
        if self.css_classes:
            add_classes_list = self.css_classes[0] if self.is_active else self.css_classes[1]
            remove_classes_list = self.css_classes[1] if self.is_active else self.css_classes[0]

            for css_class in remove_classes_list:
                self.remove_css_class(css_class)
            for css_class in add_classes_list:
                self.add_css_class(css_class)


class PlayPauseButton(ToggleButton):
    __gtype_name__ = "PlayPauseButton"

    def __init__(self, **kwargs):
        super().__init__(
            icon_names=("media-playback-pause-symbolic", "media-playback-start-symbolic"),
            **kwargs,
        )

    @GObject.Property(type=bool, default=False)
    def playing(self) -> bool:
        return super().get_active()

    @playing.setter
    def playing(self, value: bool):
        super().set_active(value)


# class PlayPauseButton(Gtk.Button):
#     __gtype_name__ = "PlayPauseButton"

#     def __init__(
#         self,
#         *,
#         func: Callable,
#         func_kwargs: dict = {},
#         default_play: bool = False,
#         play_label: str = "",
#         pause_label: str = "",
#         play_tooltip: str = "",
#         pause_tooltip: str = "",
#         **kwargs,
#     ):
#         super().__init__(**kwargs)
#         self.func = func
#         self.func_kwargs = func_kwargs
#         self.playing = default_play
#         self.play_label = play_label
#         self.pause_label = pause_label
#         self.play_tooltip = play_tooltip
#         self.pause_tooltip = pause_tooltip
#         self.play_icon_name = "media-playback-start-symbolic"
#         self.pause_icon_name = "media-playback-pause-symbolic"

#         self.btn_content = Adw.ButtonContent()
#         self.set_child(self.btn_content)

#         if not pause_label:
#             self.pause_label = self.play_label

#         if not pause_tooltip:
#             self.pause_tooltip = self.play_tooltip

#         super().connect("clicked", self._on_clicked)
#         self._update_btn_state()

#     def _on_clicked(self, button):
#         self.func(playing=self.playing, **self.func_kwargs)
#         self._update_btn_state()

#     @property
#     def is_playing(self):
#         return self.playing

#     def _update_btn_state(self):
#         if self.playing:
#             self.btn_content.set_label(self.pause_label)
#             self.btn_content.set_icon_name(self.pause_icon_name)
#             super().set_tooltip_text(self.play_tooltip)
#             self.playing = False
#         else:
#             self.btn_content.set_label(self.play_label)
#             self.btn_content.set_icon_name(self.play_icon_name)
#             super().set_tooltip_text(self.pause_tooltip)
#             self.playing = True


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
        toast_text: str = None,
        **kwargs,
    ):
        super().__init__(
            icon_name="edit-copy-symbolic", tooltip_text=tooltip_text, vexpand=False, valign=Gtk.Align.CENTER, **kwargs
        )
        self.copy_text = copy_text
        self.copy_callback = copy_callback
        self.toast_host = toast_host
        self.toast_text = toast_text
        self.connect("clicked", self.on_copy_button_clicked)

    def on_copy_button_clicked(self, *args):
        if self.copy_callback:
            self.copy_text = self.copy_callback()

        clip = super().get_clipboard()
        clip.set(str(self.copy_text))

        if self.toast_host:
            if not self.toast_text:
                self.toast_text = f"Copied '{self.copy_text}' to clipboard"

            self.toast_host.add_toast(Adw.Toast(title=self.toast_text))


class RevealButton(Gtk.ToggleButton):
    __gtype_name__ = "RevealButton"

    def __init__(self, reveal_target: Gtk.Revealer, **kwargs):
        super().__init__(
            icon_name="pan-down-symbolic",
            tooltip_text="Expand",
            vexpand=False,
            hexpand=False,
            css_classes=["flat"],
            **kwargs,
        )
        self.reveal_target = reveal_target
        self.connect("toggled", self.on_reveal_button_toggled)

    @property
    def revealed(self):
        return self.get_active()

    def on_reveal_button_toggled(self, *args):
        if self.revealed:
            # self.set_icon_name("pan-down-symbolic")
            self.reveal_target.set_reveal_child(True)

        else:
            # self.set_icon_name("pan-end-symbolic")
            self.reveal_target.set_reveal_child(False)
