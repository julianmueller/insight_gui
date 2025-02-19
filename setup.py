import os
import subprocess
import sys
from pathlib import Path
from setuptools import find_packages, setup
from setuptools.command.install import install as _install
from setuptools.command.develop import develop as _develop

package_name = "insight_gui"

base_dir = Path(__file__).parent.resolve()
data_dir = base_dir / package_name / "data"
gresource_file = data_dir / "resources.gresource"

if not gresource_file.exists():
    # Just touch it so 'data_files' can see it
    gresource_file.touch()


# find files in data folder
def collect_data_files(*suffixes: list[str]):
    # return [str(file_path) for file_path in data_dir.rglob("*") if file_path.suffix in suffixes]
    return [str(file_path) for file_path in (Path(package_name) / "data").rglob("*") if file_path.suffix in suffixes]


# compile the gresources for the gtk4 application (here mainly used for svg-icons)
def compile_gresources():
    resources_xml_file = data_dir / "resources.gresource.xml"

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
    except subprocess.CalledProcessError:
        sys.exit("Failed to compile gresources")


class InstallWithGResources(_install):
    def run(self):
        compile_gresources()
        super().run()


# only used when "--symlink-install" is used
class DevelopWithGResources(_develop):
    def run(self):
        compile_gresources()
        super().run()


setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/data", collect_data_files(".css", ".gresource")),
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
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "main = insight_gui.main:main",
        ]
    },
    cmdclass={
        "install": InstallWithGResources,
        "develop": DevelopWithGResources,
    },
)
