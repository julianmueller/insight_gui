# =============================================================================
# controller_manager_page.py
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

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, List, Tuple

import gi

gi.require_version("Adw", "1")
from gi.repository import Adw, GLib

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.widgets.buttons import ToggleButton

try:  # pragma: no cover - optional dependency that might be missing on CI
    from controller_manager_msgs.srv import ListControllers as ListControllersSrv
    from controller_manager_msgs.srv import SwitchController as SwitchControllerSrv
    from controller_manager_msgs.msg import ControllerState

    HAS_CONTROLLER_MANAGER_MSGS = True
except ImportError:  # pragma: no cover - gracefully handle environments without ros2_control
    ListControllersSrv = None
    SwitchControllerSrv = None
    HAS_CONTROLLER_MANAGER_MSGS = False


@dataclass(slots=True)
class ControllerInfo:
    name: str
    state: str
    type_name: str
    claimed_interfaces: Tuple[str, ...]
    required_command_interfaces: Tuple[str, ...]
    required_state_interfaces: Tuple[str, ...]


@dataclass(slots=True)
class ControllerManager:
    prefix: str
    display_name: str
    list_service: str
    switch_service: str


# TODO do the GObject refactor for the entire page
class ControllerManagerPage(ContentPage):
    __gtype_name__ = "ControllerManagerPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Controllers")
        super().set_placeholder_text("No controllers to show")
        super().set_search_entry_placeholder_text("Search controllers")
        super().set_refresh_fail_text(
            "No controller managers found. Start a ros2_control controller manager and refresh."
        )

        if not HAS_CONTROLLER_MANAGER_MSGS:
            super().set_refresh_fail_text(
                "controller_manager_msgs is not available. Install ros2_control to manage controllers."
            )

        self.manager_groups: List[PrefGroup] = []
        self.managers: Dict[str, ControllerManager] = {}
        self.controller_data: List[Tuple[ControllerManager, List[ControllerInfo]]] = []
        self.refresh_messages: List[Tuple[str, str]] = []

    # ------------------------------------------------------------------
    # Refresh handling
    # ------------------------------------------------------------------
    def refresh_bg(self) -> bool:
        self.controller_data = []
        self.refresh_messages = []

        if not HAS_CONTROLLER_MANAGER_MSGS:
            # Update banner text and clear UI on the main loop.
            self.set_refresh_fail_text(
                "controller_manager_msgs is not available. Install ros2_control to manage controllers."
            )
            GLib.idle_add(self.reset_ui)
            return False

        # Discover controller managers first.
        discovered_managers = self._discover_controller_managers()
        self.managers = discovered_managers

        if not discovered_managers:
            self.set_refresh_fail_text(
                "No controller managers found. Start a ros2_control controller manager and refresh."
            )
            GLib.idle_add(self.reset_ui)
            return False

        # Query controllers for each manager.
        for manager in discovered_managers.values():
            controllers, error_message = self._list_controllers(manager)

            if error_message:
                self.refresh_messages.append(("error", f"{manager.display_name}: {error_message}"))
                continue

            self.controller_data.append((manager, controllers))

        if not self.controller_data:
            self.set_refresh_fail_text("Failed to query controllers. Check controller manager logs.")
            GLib.idle_add(self.reset_ui)
            return False

        # Sort the controller data for a consistent UI order.
        self.controller_data.sort(key=lambda item: item[0].display_name)
        return True

    def refresh_ui(self):
        for manager, controllers in self.controller_data:
            group = self.pref_page.add_group(title=manager.display_name, description="Controllers")
            self.manager_groups.append(group)

            if not controllers:
                group.set_placeholder_text("No controllers reported")
                continue

            for controller in sorted(controllers, key=lambda info: info.name):
                subtitle_parts = []
                if controller.type_name:
                    subtitle_parts.append(controller.type_name)
                if controller.state:
                    subtitle_parts.append(controller.state.replace("_", " ").title())
                subtitle = " • ".join(subtitle_parts)

                row = PrefRow(title=controller.name, subtitle=subtitle)
                row.add_filter_tag(manager.display_name.lower())

                if controller.state:
                    row.add_filter_tag(controller.state.lower())
                if controller.type_name:
                    row.add_filter_tag(controller.type_name.lower())

                for interface_name in controller.claimed_interfaces:
                    row.add_filter_tag(interface_name.lower())

                tooltip_lines = []
                if controller.claimed_interfaces:
                    tooltip_lines.append("Claimed interfaces:\n  " + "\n  ".join(sorted(controller.claimed_interfaces)))
                if controller.required_command_interfaces:
                    tooltip_lines.append(
                        "Required command interfaces:\n  " + "\n  ".join(sorted(controller.required_command_interfaces))
                    )
                if controller.required_state_interfaces:
                    tooltip_lines.append(
                        "Required state interfaces:\n  " + "\n  ".join(sorted(controller.required_state_interfaces))
                    )

                if tooltip_lines:
                    row.set_tooltip_text("\n\n".join(tooltip_lines))

                # Add a textual state indicator.
                if controller.state:
                    row.add_suffix_lbl(controller.state.replace("_", " ").title())

                toggle_btn = ToggleButton(
                    func=self._on_toggle_controller,
                    func_kwargs={
                        "manager_prefix": manager.prefix,
                        "controller_name": controller.name,
                    },
                    default_active=controller.state.lower() == "active",
                    labels=("Deactivate", "Activate"),
                    icon_names=("media-playback-stop-symbolic", "media-playback-start-symbolic"),
                    tooltip_texts=("Deactivate controller", "Activate controller"),
                )
                toggle_btn.add_css_class("flat")

                # Allow toggling only for controllers that support activation/deactivation.
                if controller.state.lower() not in {"active", "inactive"}:
                    toggle_btn.set_sensitive(False)
                    toggle_btn.set_tooltip_text("Controller cannot be toggled in its current state")

                row.add_suffix(toggle_btn)
                group.add_row(row)

            group.set_description_to_row_count()

        self.pref_page.sort_groups()
        self.reapply_filters()

        for level, message in self.refresh_messages:
            if level == "error":
                self.show_toast(
                    message,
                    priority=Adw.ToastPriority.HIGH,
                    timeout=4,
                )
            else:
                self.show_toast(message)

    def reset_ui(self):
        for group in reversed(self.manager_groups):
            self.pref_page.remove_group(group)
        self.manager_groups.clear()
        self.controller_data = []

    # ------------------------------------------------------------------
    # Data discovery helpers
    # ------------------------------------------------------------------
    def _discover_controller_managers(self) -> Dict[str, ControllerManager]:
        managers: Dict[str, ControllerManager] = {}

        services = self.ros2_connector.refresh_services_store()
        suffix = "/list_controllers"

        if not services:
            return managers

        for service in services:
            if not service.full_name.endswith(suffix):
                continue

            if not any(type_name.endswith("/ListControllers") for type_name in service.type_names):
                continue

            prefix = service.full_name[: -len(suffix)]
            display_name = prefix if prefix else "/"

            list_service = service.full_name
            switch_service = self._build_service_name(prefix, "switch_controller")

            managers[prefix] = ControllerManager(
                prefix=prefix,
                display_name=display_name,
                list_service=list_service,
                switch_service=switch_service,
            )

        return managers

    def _list_controllers(self, manager: ControllerManager) -> Tuple[List[ControllerInfo], str]:
        if not ListControllersSrv or not self.ros2_connector.is_running:
            return [], "ROS 2 node is not running"

        request = ListControllersSrv.Request()

        try:
            response = self.ros2_connector.call_service(
                ListControllersSrv,
                manager.list_service,
                request,
                timeout_sec=3,
            )
        except Exception as exc:  # pragma: no cover - depends on ROS environment
            self.ros2_connector.log(
                f"Failed to list controllers for {manager.display_name}: {exc}",
                level="error",
            )
            return [], str(exc)

        controllers_field = getattr(response, "controller", None)
        if controllers_field is None:
            controllers_field = getattr(response, "controllers", [])

        controllers: List[ControllerInfo] = []

        for controller_state in controllers_field:
            controllers.append(self._controller_state_to_info(controller_state))

        return controllers, ""

    def _controller_state_to_info(self, controller_state: "ControllerState") -> ControllerInfo:
        name = getattr(controller_state, "name", "")
        state = getattr(controller_state, "state", "")
        type_name = getattr(controller_state, "type", "")

        claimed_interfaces = tuple(getattr(controller_state, "claimed_interfaces", []) or [])
        required_command_interfaces = tuple(getattr(controller_state, "required_command_interfaces", []) or [])
        required_state_interfaces = tuple(getattr(controller_state, "required_state_interfaces", []) or [])

        return ControllerInfo(
            name=name,
            state=state,
            type_name=type_name,
            claimed_interfaces=claimed_interfaces,
            required_command_interfaces=required_command_interfaces,
            required_state_interfaces=required_state_interfaces,
        )

    # ------------------------------------------------------------------
    # Toggle handling
    # ------------------------------------------------------------------
    def _on_toggle_controller(
        self,
        toggle_btn: ToggleButton,
        should_activate: bool,
        *,
        manager_prefix: str,
        controller_name: str,
    ):
        toggle_btn.set_sensitive(False)

        previous_state = not should_activate

        def worker():
            success, message = self._switch_controller(manager_prefix, controller_name, should_activate)

            def finish():
                try:
                    toggle_btn.set_sensitive(True)
                except Exception:  # pragma: no cover - widget might be destroyed during refresh
                    return False

                if not success:
                    self._restore_toggle(toggle_btn, previous_state)
                    failure_msg = (
                        f"Failed to {'activate' if should_activate else 'deactivate'} {controller_name}: {message}"
                    )
                    self.show_toast(
                        failure_msg,
                        priority=Adw.ToastPriority.HIGH,
                        timeout=4,
                    )
                else:
                    self.show_toast(
                        f"{controller_name} {'activated' if should_activate else 'deactivated'}",
                        priority=Adw.ToastPriority.NORMAL,
                        timeout=3,
                    )
                    self.refresh()

                return False

            GLib.idle_add(finish)

        threading.Thread(target=worker, daemon=True).start()

    def _restore_toggle(self, toggle_btn: ToggleButton, active: bool):
        try:
            toggle_btn.handler_block_by_func(toggle_btn._on_toggle)  # type: ignore[attr-defined]
            toggle_btn.set_active(active)
            toggle_btn.handler_unblock_by_func(toggle_btn._on_toggle)  # type: ignore[attr-defined]
            toggle_btn.update_button()
        except Exception:  # pragma: no cover - defensive programming
            pass

    def _switch_controller(
        self,
        manager_prefix: str,
        controller_name: str,
        activate: bool,
    ) -> Tuple[bool, str]:
        manager = self.managers.get(manager_prefix)

        if not manager or not SwitchControllerSrv or not self.ros2_connector.is_running:
            return False, "Switch service is unavailable"

        request = SwitchControllerSrv.Request()

        self._set_switch_request_lists(request, controller_name, activate)
        self._set_switch_request_flags(request)

        try:
            response = self.ros2_connector.call_service(
                SwitchControllerSrv,
                manager.switch_service,
                request,
                timeout_sec=5,
            )
        except Exception as exc:  # pragma: no cover - depends on ROS environment
            self.ros2_connector.log(
                f"Failed to switch controller {controller_name}: {exc}",
                level="error",
            )
            return False, str(exc)

        success = self._extract_switch_success(response)
        message = self._extract_switch_message(response)

        return success, message

    def _set_switch_request_lists(self, request, controller_name: str, activate: bool):
        activate_list = [controller_name] if activate else []
        deactivate_list = [controller_name] if not activate else []

        self._assign_request_field(request, "activate_controllers", activate_list)
        self._assign_request_field(request, "deactivate_controllers", deactivate_list)
        self._assign_request_field(request, "start_controllers", activate_list)
        self._assign_request_field(request, "stop_controllers", deactivate_list)

    def _set_switch_request_flags(self, request):
        if hasattr(request, "strictness"):
            try:
                best_effort = getattr(request, "BEST_EFFORT")
            except AttributeError:
                try:
                    best_effort = getattr(type(request), "BEST_EFFORT")
                except AttributeError:
                    best_effort = None

            if best_effort is not None:
                request.strictness = best_effort
            else:
                current_value = getattr(request, "strictness")
                if isinstance(current_value, bool):
                    request.strictness = True
                else:
                    request.strictness = 2

        for field_name in ("start_asap", "activate_asap"):
            if hasattr(request, field_name):
                setattr(request, field_name, True)

        if hasattr(request, "timeout"):
            setattr(request, "timeout", 0.0)

    def _assign_request_field(self, request, field_name: str, values: List[str]):
        if hasattr(request, field_name):
            try:
                setattr(request, field_name, list(values))
            except Exception:
                setattr(request, field_name, values)

    def _extract_switch_success(self, response) -> bool:
        if hasattr(response, "ok"):
            return bool(getattr(response, "ok"))
        if hasattr(response, "success"):
            return bool(getattr(response, "success"))
        if hasattr(response, "result"):
            return bool(getattr(response, "result"))
        return True

    def _extract_switch_message(self, response) -> str:
        for field_name in ("error_message", "status_message", "reason"):
            if hasattr(response, field_name):
                field_value = getattr(response, field_name)
                if field_value:
                    return str(field_value)

        if hasattr(response, "error_messages"):
            messages = getattr(response, "error_messages")
            if isinstance(messages, (list, tuple)) and messages:
                return ", ".join(str(msg) for msg in messages)

        return ""

    def _build_service_name(self, prefix: str, suffix: str) -> str:
        base = prefix.rstrip("/")
        if not base:
            return f"/{suffix}"
        return f"{base}/{suffix}"
