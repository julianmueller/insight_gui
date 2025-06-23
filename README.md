<h1 align="center">
  <img src="insight_gui/data/logo/insight.svg" alt="Insight" height="170"/>
  <br>
  Insight - a minimalist GUI for ROS2
</h1>

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

## List of Feature

- show and filter lists of:
    - all packages on the system and their respective info,
    - all running nodes with their topics/services/actions/parameters etc,
    - all available topics with their respective msg types and publishers/subscribers,
    - all available services with their respective msg types and servers/clients,
    - all available actions with their respective msg types and servers/clients,
    - all msg types of messages/services/actions,
- inspect packages with their executables
- create new packages via a dialog
- inspect nodes with their subscribers, publishers, parameters etc
- inspect message definitions (with names and data types) and copy raw contents
- traverse through msg definitions (like PoseArray > Pose > Position > x)
- filter all lists where it is useful
- call services and specify the request data
- calculate tf transforms between two frames
- get parameters from nodes
- show images from topics (as single or continuous stream)
- show current ros2 clock/time
- manipulate ros2 env variables like ROS_DOMAIN_ID for the running GUI session
- show ros2 logs and filter them
- show ros2 doctor inspection with available package updates etc
- every page is deteachable into its own floating window

## License

GPLv3. See [LICENSE](LICENSE).