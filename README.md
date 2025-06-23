<h1 align="center">
  <img src="insight_gui/data/icons/scalable/actions/insight.svg" alt="Insight" height="170"/>
  <br>
  Insight - a minimalist GUI for ROS2
</h1>

Insight is a minimalist GUI alternative to rqt. It is a GTK4-based tool for exploring ROS2 topics, services, and messages, featuring the GNOME Adwaita style.

## Features

<details>
<summary>Nodes</summary>

### Node List Page

<img src="docs/screenshots/node_list_page.png" alt="Node List" width="400"/>

- Browse all active ROS2 nodes
- Group nodes by namespace
- Search and filter nodes
- View hidden nodes

### Node Info Page

<img src="docs/screenshots/node_info_page.png" alt="Node Info" width="400"/>

- View detailed node information
- Display node publishers, subscribers
- Show service clients and servers and action clients and servers
- Show Node parameters and jump to the parameter edit page
</details>

<details>
<summary>Topics</summary>
    
### Topic List Page

<img src="docs/screenshots/topic_list_page.png" alt="Topic List" width="400"/>
    
- Browse all available ROS2 topics
- Group topics by namespace
- Search and filter topics
- View topic types and hidden topics

### Topic Info Page

<img src="docs/screenshots/topic_info_page.png" alt="Topic Info" width="400"/>

- View detailed topic information
- Display topic interface types and their definition
- Show publishers and subscribers

### Topic Publisher Page

<img src="docs/screenshots/topic_pub_page.png" alt="Topic Publisher" width="400"/>

- Publish messages to ROS2 topics
- Edit the published message as YAML/JSON/CSV
- Publish once or as continuous stream

### Topic Subscriber Page

<img src="docs/screenshots/topic_sub_page.png" alt="Topic Subscriber" width="400"/>

- Subscribe to ROS2 topics
- Receive messages as YAML/JSON/CSV
- Message history and filtering
- Get only one message or the continuous stream
</details>

<details>
<summary>Services</summary>

### Service List Page

<img src="docs/screenshots/service_list_page.png" alt="Service List" width="400"/>

- Browse all available ROS2 services
- Group services by namespace
- Search and filter services
- View service types and hidden services

### Service Info 

<img src="docs/screenshots/service_info_page.png" alt="Service Info" width="400"/>

- View detailed service information
- Show service providers
- Display service request/response interface type and definition
- Quickly jump to the service call page

### Service Call Page

<img src="docs/screenshots/service_call_page.png" alt="Service Call" width="400"/>

- Call ROS2 services
- Edit the service request as YAML/JSON/CSV
- View service responses

</details>

<details>
<summary>Actions</summary>

### Action List Page

<img src="docs/screenshots/action_list_page.png" alt="Action List" width="400"/>

- Browse all available ROS2 actions
- Group actions by namespace
- Search and filter actions
- View action types

### Action Info Page

<img src="docs/screenshots/action_info_page.png" alt="Action Info" width="400"/>

- View detailed action information
- Display action interface type and definition
- Show action servers and clients
- Access goal/result/feedback structure

### Action Goal Page

<img src="docs/screenshots/action_goal_page.png" alt="Action Goal" width="400"/>

- Send goals to ROS2 action servers
- Edit the goal message as YAML/JSON/CSV
- View feedback and results
</details>

<details>
<summary>Parameters</summary>

### Parameter List Page

<img src="docs/screenshots/param_list_page.png" alt="Parameter List" width="400"/>

- Browse all ROS2 parameters
- Group parameters by node
- Search and filter parameters
- View parameter types and values

### Parameter Edit Page

<img src="docs/screenshots/param_edit_page.png" alt="Parameter Edit" width="400"/>

- Edit ROS2 parameter values
- Support for different parameter types
- Real-time parameter updates
- Parameter validation
</details>

<details>
<summary>Packages</summary>

### Package List Page

<img src="docs/screenshots/pkg_list_page.png" alt="Package List" width="400"/>

- Browse all ROS2 packages
- Search and filter packages
- View package information

### Package Info Page

<img src="docs/screenshots/pkg_info_page.png" alt="Package Info" width="400"/>

- View detailed package information
- Show package executables
- Access package metadata
- Display package dependencies

### New Package Dialog

<img src="docs/screenshots/pkg_new_dialog.png" alt="New Package Dialog" width="400"/>

- Create new ROS2 packages
- Configure package settings
- Set dependencies and build type
- Specify destination directory
</details>

<details>
<summary>Launch Files</summary>

### Launch List Page

<img src="docs/screenshots/launch_list_page.png" alt="Launch List" width="400"/>

- Browse available launch files
- Search and filter launch files
- View launch file information

### Launch Info Page

<img src="docs/screenshots/launch_info_page.png" alt="Launch Info" width="400"/>

- ! STILL EXPERIMENTAL !
- View launch file details
- Display launch arguments, and started nodes
- Launch file execution
</details>

<details>
<summary>Interfaces</summary>

### Interface Browser Page

<img src="docs/screenshots/interface_browser_page.png" alt="Interface Browser" width="400"/>

- Browse ROS2 message/service/action interfaces
- Interfaces are grouped by their packages
- Switch between all/msgs/srvs/actions interfaces types
- Access interface infos

### Interface Info Page

<img src="docs/screenshots/interface_info_page.png" alt="Interface Info" width="400"/>

- View interface constants
- Separate message / service (request/response) / action (goal/feedback/result)
- Navigate through nested interfaces
- Open interface definitions in a separate text editor or show it online
- View detailed interface definitions
- Display default values for basic data types (like int, string etc)

### Interface Definition Page

<img src="docs/screenshots/interface_definition_page.png" alt="Interface Definition" width="400"/>

- Show raw interface definition as YAML/JSON/CSV
- Copy string representation into clipboard

</details>

<details>
<summary>Misc</summary>

### TF Page

<img src="docs/screenshots/tf_page.png" alt="TF Page" width="400"/>

- View TF transformation tree
- Display coordinate frames
- Show frame relationships

### Image Viewer Page

<img src="docs/screenshots/img_viewer_page.png" alt="Image Viewer" width="400"/>

- Display ROS2 image topics
- Show images as single shot or continuous stream
- Image format support
- Display image meta data


### Teleop 

<img src="docs/screenshots/teleop_page.png" alt="Teleop Page" width="400"/>

- Robot teleoperation interface with Twist (and later Joy)
- Control it via direction buttons or via keyboard

### Graph Page

<img src="docs/screenshots/graph_page.png" alt="Graph View" width="400"/>

- ! STILL EXPERIMENTAL !
- Visualize ROS2 node-topic connections
- Interactive graph layout
- Quickly jump to respectify info page for further info on the node/topic

### Joint States Page

<img src="docs/screenshots/joint_states_page.png" alt="Joint States" width="400"/>

- ! STILL EXPERIMENTAL !
- Monitor robot joint states
</details>

<details>
<summary>Diagnosis</summary>

### Doctor Page

<img src="docs/screenshots/doctor_page.png" alt="Doctor Page" width="400"/>

- ROS2 system diagnostics
- Network configuration check
- Package version information
- QoS compatibility analysis

### Logger Page

<img src="docs/screenshots/logger_page.png" alt="Logger Page" width="400"/>

- View ROS2 log messages
- Filter logs by severity
- Regex search for messages and nodes
</details>

<details>
<summary>GUI Features</summary>

### Preferences Dialog

<img src="docs/screenshots/preferences_dialog.png" alt="Preferences" width="400"/>

- Change the settings of the application
- Set ROS2 environmental variables
- Theme and appearance options
- Behavior configuration

### Multi-Window Support

<img src="docs/screenshots/multi_window_use_case.png" alt="Multi-Window" width="400"/>

- Multiple windows via detachable pages

### Shortcuts

- `CTRL+R` or `F5` triggers a refresh of the page
- `CTRL+F` triggers the search on every page
- `CTRL+D` detaches the current page into a new window
- `CTRL+ENTER` triggers the pages main action (like publish)
- `CTRL+Q` closes the current window

### Appearance

- DARK THEME! (depending on the current system theme)
</details>


## Prerequisites

Install the following packages, as some currently cannot be installed by rosdep (I'm working on it).

```bash
sudo apt install libgtk-4-dev libgirepository1.0-dev adwaita-icon-theme libadwaita-1-dev libglib2.0-dev python3-gi python3-gi-cairo python3-networkx python3-graphviz
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

## License

GPLv3. See [LICENSE](LICENSE).
