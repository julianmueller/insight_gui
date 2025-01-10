import os
from pathlib import Path

from ros2pkg.api import get_executable_paths
from ament_index_python.packages import get_packages_with_prefixes

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.helpers.content_page import ContentPage
from insight_gui.widgets.helpers.pref_row import PrefRow


class PackageListPage(Adw.NavigationPage):
    __gtype_name__ = "PackageListPage"

    def __init__(self, nav_view: Adw.NavigationView = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Package List")

        self.nav_view = nav_view if nav_view else self.get_parent()

        self.content_page = ContentPage(refresh_func=self.refresh)
        self.content_page.set_search_entry_placeholder_text("Search for Nodes")
        super().set_child(self.content_page)

        self.list_group = self.content_page.pref_page.add_group(empty_msg="No packages found")

    def refresh(self, *args):
        self.list_group.clear()

        available_pkgs = get_packages_with_prefixes()

        for pkg_name, pkg_path in available_pkgs.items():
            row = PrefRow(title=pkg_name, subtitle=pkg_path)
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=PackageInfoPage,
                pkg_name=pkg_name,
                pkg_path=pkg_path,
            )
            self.list_group.add_row(row)

        return bool(self.content_page.pref_page.num_groups)


class PackageInfoPage(Adw.NavigationPage):
    __gtype_name__ = "PackageInfoPage"

    def __init__(
        self,
        pkg_name: str,
        pkg_path: str,
        nav_view: Adw.NavigationView = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().set_title(f"Package '{pkg_name}'")

        self.pkg_name = pkg_name
        self.nav_view = nav_view if nav_view else self.get_parent()

        self.content_page = ContentPage(search_enabled=True, refresh_enabled=False)
        super().set_child(self.content_page)

        # add open btn
        self.content_page.add_header_btn(
            icon_name="folder-symbolic",
            tooltip_text="Open Package Folder",
            func=self.on_open_pkg_folder,
            pkg_path=pkg_path,
            pkg_name=pkg_name,
        )

        # Executables
        executables_group = self.content_page.pref_page.add_group(
            title="Executables", empty_msg="Package has no executables"
        )
        executable_paths = get_executable_paths(package_name=pkg_name)

        for path in sorted(executable_paths):
            executable_name = Path(path).name
            row = PrefRow(title=executable_name)
            row.add_suffix_btn(
                icon_name="edit-copy-symbolic",
                tooltip_text="Copy 'ros2 run' command",
                func=self.on_copy_executable,
                pkg_name=pkg_name,
                executable_name=executable_name,
            )
            # TODO maybe add a copy btn, so the user can past the "ros2 run/launch" command directly somewhere?
            # row.set_subpage_link(
            #     nav_view=self.nav_view,
            #     subpage_class=NodeInfoPage,
            #     node_name=node_name,
            #     node_namespace=node_namespace,
            #     node_full_name=node_full_name,
            #     ros2_node=self.ros2_node,
            # )
            executables_group.add_row(row)

        # add the counts as descriptions
        executables_group.set_description_to_row_count()

    def on_copy_executable(self, pkg_name: str, executable_name: str):
        # TODO add also roslaunch?
        cmd = f"ros2 run {pkg_name} {executable_name}"
        clip = self.get_clipboard()
        clip.set(cmd)
        self.content_page.show_toast(f"copied '{cmd}'")

    def on_open_pkg_folder(self, *, pkg_path: str, pkg_name: str):
        path = (Path(pkg_path) / "share" / pkg_name).resolve()
        if os.path.isdir(path):
            os.system(rf"xdg-open {path}")
        else:
            self.content_page.show_toast(f"Path '{path}' does not exist!")
