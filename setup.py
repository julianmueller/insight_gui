from pathlib import Path
from setuptools import find_packages, setup

package_name = "insight_gui"


# includes svg and png files in the shared folders
def collect_data_files():
    data_files = []
    data_dir = Path(package_name) / "data"

    # Collect .svg and .png files from the 'data' directory
    for file_path in data_dir.rglob("*"):
        if file_path.suffix in {".svg", ".png", ".xml"}:
            # Convert Path object to string for data_files
            data_files.append(str(file_path))

    return data_files


setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/data", collect_data_files()),
    ],
    package_data={
        "": ["*.ui"],  # this is important, for ros2 to find the ui files!
    },
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Julian Müller",
    maintainer_email="julian.mueller@iwb.tum.de",
    url="https://github.com/julianmueller/insight_gui",
    keywords=["ROS2", "GUI", "GTK4"],
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
)
