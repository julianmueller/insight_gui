<h1 align="center">
  <img src="insight_gui/data/logo/insight-logo.svg" alt="Insight" height="170"/>
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


## TODO List

- marketing
    - make a proper logo (help!)
    - redo all screenshots before release
- features
    - make "set parameter" work
    - make btns of img viewer work
    - add tf inspection page (show the stuff that rviz shows)
    - add a controller "/joy" page (also look into Workbench - Gamepad Demo)
    - add a teleop page
    - add an "echo" group for topics info page, to listen to current data on the topic (maybe also for services and actions?)
    - ?add every page of the gui as a ros2 executable, so a window with only this page starts
    - add constants to be visible in msg definitions (like ur_msgs/msg/SetIO)
    - add the ros wiki explainations for packages? like what are all possible subscribed/published topics? or just a btn?
    - find a way to load all "refresh" content on startup, also if one page updates "available_nodes" etc, all other pages that utilize this shall update as well
    - check continuous img stream
    - extend preferences dialog
    - add option to add new env variables in the pref dialog (and add a refresh btn)
    - add a launch page to directly launch nodes with a set of arguments
    - add a refresh to all "static" pages, e.g. TopicInfoPage, as this might also change while it is open
    - add when a new window is opened as a detach, make it have the same content as the detached content_page
    - add for all row descriptions etc a max line limit! (robot description param hold the whole urdf file, which results in a mile long description) so it is concat after some content length
- cleanup
    - remove "status_page" in window.ui
    - rename all function, to fit GTK style "on_xxx" and "do_xxx"
    - merge all "msg_type_info_page" etc into one class when differs in what it displays depending on the interface type
- gnome/gtk4
    - make shortcuts (eg CTRL+F) work and add shortcuts page (they should also work via actions and for detached windows)
    - add gtk action for all major actions
    - add gtk settings
    - add Gtk/Gio Notifications
    - replace "webbrowser" stuff with gtk File/Web Launcher

## License

GPLv3. See [LICENSE](LICENSE).