# ros2_insight

Insight is a minimalist GUI alternative to rqt. It is a GTK4-based tool for exploring ROS2 topics, services, and messages, featuring the GNOME Adwaita style.

## Prerequisites

Install the following packages, as (some) cannot be installed by rosdep (working on it).

```bash
sudo apt install python3-gi python3-gi-cairo libgtk-4-dev libgirepository1.0-dev adwaita-icon-theme libadwaita-1-dev
```

## Installation

### Binary Install with apt

! THIS IS NOT WORKING YET, but hopefully will in the future (I'm waiting for approval) !

```bash
sudo apt install ros-jazzy-insight-gui
```

### Install from Source

1. Create the workspace and clone this repo:

```bash
mkdir -p ros2_ws/src
cd ros2_ws/src
git clone https://github.com/julianmueller/insight_gui
```

If you want the `jazzy-dev` branch, where I'm currently working on the latest features, use:

```bash
git clone -b jazzy-dev https://github.com/julianmueller/insight_gui
```

2. Install dependencies with rosdep:

```bash
rosdep install --from-paths src -y --ignore-src
```

3. Build the workspace:

```bash
colcon build --symlink-install
source install/setup.bash
```

## Execution

Like every other ros2 node, the GUI is started by:

```bash
ros2 run insight_gui main
```