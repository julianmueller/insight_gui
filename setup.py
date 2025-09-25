# setup.py
#
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

import os
import shutil
import subprocess
import sys
from pathlib import Path
from setuptools import find_packages, setup
from setuptools.command.install import install as _install
from setuptools.command.develop import develop as _develop

package_name = "insight_gui"

base_dir = Path(__file__).parent.resolve()
data_dir = base_dir / package_name / "data"
gresource_file = data_dir / "resources.gresource"  # compiled GResource file
gschema_file = data_dir / "geschemas.compiled"  # compiled GSettings schema file


if not gresource_file.exists():
    # Just touch it so 'data_files' can see it
    gresource_file.touch()


# find files in data folder
def collect_data_files(*suffixes: list[str]):
    # return [str(file_path) for file_path in data_dir.rglob("*") if file_path.suffix in suffixes]
    return [str(file_path) for file_path in (Path(package_name) / "data").rglob("*") if file_path.suffix in suffixes]


# compile the gresources for the gtk4 application (here mainly used for svg-icons)
def compile_gresources():
    resources_xml_file = data_dir / "com.github.julianmueller.Insight.gresource.xml"

    # Run glib-compile-resources inline
    try:
        subprocess.run(
            [
                "glib-compile-resources",
                f"--target={gresource_file}",
                f"--sourcedir={data_dir}",
                "--generate",
                "--manual-register",
                resources_xml_file,
            ],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        sys.exit(
            "Error: glib-compile-resources not found. Install it with e.g. sudo apt-get install libglib2.0-dev-bin"
        )
    except (subprocess.CalledProcessError, PermissionError, OSError) as e:
        sys.exit(f"Failed to compile GResources: {e}")


# install GSettings schema for persistent preferences
def install_gsettings_schema():
    # gschema_xml_file = data_dir / f"com.github.julianmueller.Insight.gschema.xml"
    # TODO maybe install install into GLib.user_data_dir() instead own ros dir

    try:
        # Compile schemas
        subprocess.run(["glib-compile-schemas", data_dir], check=True, capture_output=True)

    except FileNotFoundError:
        sys.exit("Error: glib-compile-schemas not found. Install it with e.g. sudo apt-get install libglib2.0-dev-bin")

    except (subprocess.CalledProcessError, PermissionError, OSError) as e:
        sys.exit(f"Failed to compile GSettings schemas: {e}")


class InstallWithGResources(_install):
    def run(self):
        print("=== Building Insight GUI ===")

        # Compile GResources (required)
        try:
            compile_gresources()
            print("✓ GResources compilation successful")
        except Exception as e:
            print(f"✗ GResources compilation failed: {e}")
            sys.exit(1)

        # Install GSettings schema (optional, but recommended)
        try:
            install_gsettings_schema()
            print("✓ GSettings schema installation successful")
        except Exception as e:
            print(f"⚠ GSettings schema installation error: {e}")

        super().run()
        print("=== Insight GUI build completed ===")


# only used when "--symlink-install" is used
class DevelopWithGResources(_develop):
    def run(self):
        print("=== Building Insight GUI (development mode) ===")

        # Compile GResources (required)
        try:
            compile_gresources()
            print("✓ GResources compilation successful")
        except Exception as e:
            print(f"✗ GResources compilation failed: {e}")
            sys.exit(1)

        # Install GSettings schema (optional, but recommended)
        try:
            install_gsettings_schema()
            print("✓ GSettings schema installation successful")
        except Exception as e:
            print(f"⚠ GSettings schema installation error: {e}")

        super().run()
        print("=== Insight GUI development build completed ===")


setup(
    name=package_name,
    version="0.1.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/data", collect_data_files(".css", ".xml", "png", ".gresource", ".compiled")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Julian Müller",
    maintainer_email="julian.mueller@iwb.tum.de",
    url="https://github.com/julianmueller/insight_gui",
    keywords=["ROS2", "GUI", "GTK4", "libadwaita"],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Topic :: Software Development",
    ],
    description="Minimalist GUI alternative to rqt, but based on GTK4 with Adwaita style.",
    long_description="""\
        Insight is a minimalist GUI alternative to rqt. It is a GTK4-based tool for exploring ROS2 topics,
        services, and messages, featuring the GNOME Adwaita style.""",
    license="GPL-3.0-only",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "main = insight_gui.main:main",
            "dummy_img_pub = insight_gui.dummy_img_pub:main",
            "dummy_logger = insight_gui.dummy_log_pub:main",
            "dummy_tf_broadcaster = insight_gui.dummy_tf_broadcaster:main",
            "dummy_graph = insight_gui.dummy_graph:main",
        ]
    },
    cmdclass={
        "install": InstallWithGResources,
        "develop": DevelopWithGResources,
    },
)
