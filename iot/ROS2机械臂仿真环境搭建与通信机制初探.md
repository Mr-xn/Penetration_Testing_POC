# ROS2机械臂仿真环境搭建与通信机制初探
> 常乐
> 来源：https://www.iotsec-zone.com/article/536

# 搭建ROS2以及仿真环境
## ROS2
  我推荐使用WSL，新建一个独立的虚拟机，方便给ROS一个独立的空间，有能力者可以买一个移动硬盘自己装配。
因为现在官方已经不更新ROS了，主要更新维护ROS2，我进入ROS2官网找到配置过程。   [https://docs.ros.org/en/humble/index.html](https://docs.ros.org/en/humble/index.html)
官方推荐deb包安装，但是版本是Ubuntu 26.04。我们装的是Humble，所以需要22.04。所以当前版本正好。

官方顺序：开 universe、安装 ros2-apt-source、装 ros-humble-desktop 和 rosdep，最后把环境变量写进 ~/.bashrc 并跑一次 ros2 验证。
检查代理：
![0.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditao20rym3xpocw4g.png)
```bash
sudo apt update
sudo apt install -y software-properties-common curl
sudo add-apt-repository -y universe
```
更新软件源，安装基础工具curl和software-properties-common。用来下载GPG key和ROS源配置。
紧接着开启Ubuntu的universe仓库，ROS2很多依赖都在这个仓库里面。
![1.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditaok6rlh5nyfspox.png)
然后安装ROS2官方APT软件源配置包
```bash
curl -L -o ~/ros2-apt-source.deb \
https://github.com/ros-infrastructure/ros-apt-source/releases/download/1.2.0/ros2-apt-source_1.2.0.jammy_all.deb
```
![2.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditapf80g4jkisnvbj.png)
安装deb包,更新依赖
```bash
sudo dpkg -i ~/ros2-apt-source.deb
sudo apt update
```
![3.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditapn3s0ytrucvmfr.png)
正式安装ROS2 Humble以及ROS开发环境
```bash
sudo apt install -y ros-humble-desktop python3-rosdep ros-dev-tools
```
![4.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditapso4jszyvc1dnc.png)
WSL还要装图形化工具
```bash
sudo apt update
sudo apt install -y x11-apps mesa-utils
```
![5.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditaq6xv30quwoqkmu.png)
装完后我们的desktop版本的ros就支持图形化工具了。
初始化rosdep配置，是为了创建`/etc/ros/rosdep/`让 ROS 知道去哪里获取依赖数据库。  
```bash
sudo rosdep init
```
![6.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditaqjl42j3jmch9l1.png)
更新ROS依赖数据库，类似于`apt install`但是是ROS自己的依赖索引，以后可以用`rosdep install`更新ROS
```bash
rosdep update
```
![7.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditaqso40qgtshlyrn.png)
我们看到，源都是git上的。
最后再写入环境变量
```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```
![8.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditar17e0i2en12ewi.png)
这样，以后我们在终端输入ros2就可以直接执行了。

![9.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditar56oga9owztzhu.png)

![10.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditara18k1sa5ipbup.png)
验证rviz2

![11.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditardeyubkk62jg87.png)
整体命令
```bash
sudo apt update
sudo apt install -y software-properties-common curl
sudo add-apt-repository -y universe

sudo curl -L -o /tmp/ros2-apt-source.deb \
https://github.com/ros-infrastructure/ros-apt-source/releases/download/1.2.0/ros2-apt-source_1.2.0.jammy_all.deb

sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update

sudo apt install -y ros-humble-desktop python3-rosdep ros-dev-tools

sudo rosdep init
rosdep update

echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```
创建一个目录作为ROS的开发环境，为我们以后安全研究做准备
```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws
colcon build
```

![12.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditarxktclz86ddebb.png)
IDE我们用Cursor

![13.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditas1gctaviige1pc.png)
在cursor里面点击File，打开工作目录路径，安装WSL拓展。

![14.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditas418tpq8ve0hxi.png)
`Ctrl + Shift + P`之后输入WSL， 点击`WSL: Connect to WSL using Distro...`选择`Ubuntu-22.04`

![15.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditasb72nocqztei6n.png)
连上之后看到

![16.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditasdu098d5yu8nf1.png)
点击Open Folder看到WSL目录，选择我们的工作区

![17.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditasg14ylzgjq5pbl.png)
再`Ctrl + Shift + E`按这个快捷键显示文件资源管理器

![18.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditasidthfoy3vtj4v.png)
打开终端，可以看到我们的第一个项目_init_.py

![19.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditaskt18kugba0k7t.png)
## VlA
安装Movelt 2
```bash
sudo apt update
sudo apt install -y ros-humble-moveit
sudo apt install -y ros-humble-moveit-setup-assistant
ros2 launch moveit_setup_assistant setup_assistant.launch.py
```

![20.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditau0l5y5vc4oluuo.png)

![21.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditau2q82yf2xe3xqa.png)
安装Gazebo
```bash
sudo apt install -y ros-humble-ros-gz
ros2 launch ros_gz_sim gz_sim.launch.py gz_args:=empty.sdf
```

![22.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditauaygwcftn71lxn.png)
# 控制器
```bash
sudo apt update
sudo apt install -y \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-controller-manager \
  ros-humble-joint-state-publisher-gui \
  ros-humble-gazebo-ros2-control \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-joint-trajectory-controller \
  ros-humble-diff-drive-controller \
  ros-humble-position-controllers \
  ros-humble-forward-command-controller 
sudo apt install -y ignition-fortress
```
验证控制器
```bash
/opt/ros/humble/lib/controller_manager/ros2_control_node
```

![23.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditav2pahm909k9re4.png)
表示ros2_control_node 能启动，但因为你没有给它配机器人描述和控制器参数，所以它只是空跑等待。
包装命令ros2_control_node
```bash
sudo tee /etc/profile.d/ros2_humble.sh > /dev/null <<'EOF'
source /opt/ros/humble/setup.bash
EOF
sudo chmod 644 /etc/profile.d/ros2_humble.sh
bash -lc 'echo $ROS_DISTRO && which ros2'
humble
/opt/ros/humble/bin/ros2
sudo ln -s /opt/ros/humble/lib/controller_manager/ros2_control_node /usr/local/bin/ros2_control_node
```

![24.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditavc8y19gzzxwb7p.png)
直接输入ros2_control_node

![25.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditavf03lbv72mw0st.png)
## 简单的控制器
我们拿到一个简单的机器臂包，查看简单的执行过程并分析，首先对目标包进行编译：
```bash
cd ~/ros2_ws
colcon build --packages-select arm2_description
```
编译过程中，colcon 会读取 package.xml 和 setup.py，识别该包为 ament_python 类型，并将其相关资源安装到 install/arm2_description/ 目录下。特别是 setup.py 中定义的 data_files 会将 launch、urdf 和 rviz 文件复制到包共享目录，以便 ROS2 在运行时通过包索引进行查找。
编译完成后，需要将工作区注册到当前终端环境：
```bash
source ~/ros2_ws/install/setup.bash
```
这一步的作用是补充当前终端中的 ROS2 运行环境，包括包索引路径、Python 模块路径、可执行文件路径以及动态库路径等。只有在完成环境注册后，ros2 launch 才能正确找到 arm2_description 包及其启动文件。
完成环境注册后，执行以下命令启动系统：
```bash
ros2 launch arm2_description display.launch.py
```
该命令会调用 display.launch.py，由 ROS2 launch 系统统一启动多个节点，并加载机械臂模型与 RViz 配置文件。启动后，界面中会弹出关节调节窗口和 RViz 可视化窗口。通过调节 GUI 中的关节滑块，可以观察到机械臂模型在 RViz 中随之运动。

![26.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditawlw1d1bpd4apud.png)
实验运行后，可以看到机械臂模型由底座、两段连杆和末端执行器组成，并在 RViz 中正常显示。拖动 joint_state_publisher_gui 中的关节滑块后，机械臂姿态会实时更新。该现象说明关节状态发布、坐标变换计算和三维显示链路已经建立成功。

![27.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditawob2imnx1pbfxn.png)
实验成功后我们就要去探究整个系统的组成和运行原理，arm2_description 的运行逻辑可以概括为“模型加载、状态发布、坐标计算和图形显示”四个环节。其启动入口 display.launch.py 采用 ROS2 launch API 组织整个启动过程。首先，launch 文件通过 FindPackageShare("arm2_description") 找到包的共享目录，再通过 PathJoinSubstitution 定位 urdf/arm2.urdf.xacro 和 rviz/arm2.rviz 文件。随后，利用 Command(["xacro ", xacro_file]) 在启动时解析 Xacro 文件，并将其展开为标准 URDF 描述，再以 robot_description 参数的形式传递给 robot_state_publisher。
系统启动后，joint_state_publisher_gui 节点负责为用户提供图形化的关节调节界面，并将关节状态发布到 /joint_states 话题。robot_state_publisher 节点读取 robot_description 中定义的机械臂结构信息，并订阅 /joint_states，根据当前关节角度计算各连杆之间的坐标变换关系，进一步发布 /tf 和 /tf_static。rviz2 节点则根据机器人模型描述和 TF 数据，在三维界面中绘制机械臂的实时姿态。
因此，该系统的核心数据流可以表示为：
```bash
joint_state_publisher_gui
        ↓
    /joint_states
        ↓
robot_state_publisher
        ↓
   /tf 与 /tf_static
        ↓
       rviz2
```
这表明三个节点并不是简单地“互相连接”，而是借助 ROS2 的话题机制和 TF 机制实现协同工作。
```
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
rqt_graph
```

![28.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditaxayykg7t05juue.png)
### 机械臂模型结构分析
arm2.urdf.xacro 定义了一个简化的两关节机械臂模型。该模型包含四个 link，分别是 base_link、link1、link2 和 tool_link。其中，base_link 表示底座，link1 与 link2 分别表示机械臂的两段连杆，tool_link 表示末端执行器。模型使用圆柱体和球体等基础几何结构构造，并通过不同材质颜色进行区分。
在关节定义方面，该机械臂包含三个 joint：
● joint1：连接 base_link 与 link1，类型为 revolute，绕 Z 轴旋转，运动范围为 -3.14 到 3.14。
● joint2：连接 link1 与 link2，类型为 revolute，绕 Y 轴旋转，运动范围为 -1.57 到 1.57。
● tool_fixed_joint：连接 link2 与 tool_link，类型为 fixed，表示末端执行器与第二连杆固定连接。
从机器人描述角度看，URDF 的作用是用“连杆 - 关节”树状结构表达机器人本体几何关系和运动学关系。对于 robot_state_publisher 来说，URDF 不仅提供模型显示所需的形状信息，也为其计算各坐标系之间的变换关系提供了依据。

![29.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditaxrdg90mpg0rxhc.png)
### ROS2通信机制初步分析
虽然本实验只涉及基础可视化功能，但已经体现出 ROS2 的典型分布式架构特征。系统中的各节点通过 Topic 机制交换消息，通过 TF 维护空间坐标关系，并由 Launch 系统统一组织运行。对于用户而言，直接可见的是节点、话题、参数和可视化界面；但这些上层功能的底层实现，依赖的是 ROS2 的中间件接口层和 DDS 通信机制。
在 ROS2 中，应用层通过 ROS2 API 发布和订阅消息，而消息的发现与传输由 ROS Middleware（RMW）接口向下适配具体中间件实现。在 ROS2 Humble 中，默认常用的中间件实现是 Fast DDS。也就是说，当 joint_state_publisher_gui 发布 /joint_states 消息时，ROS2 并不是直接自行完成网络通信，而是通过 RMW 调用 Fast DDS 实现节点发现、话题发现、发布订阅和消息传输。
因此，从分层角度看，该系统可以理解为：
● 应用层：joint_state_publisher_gui、robot_state_publisher、rviz2
● 客户端层：ROS2 的 Node、Topic、Parameter、Launch、TF
● 接口层：RMW
● 中间件层：DDS（Fast DDS）

![30.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditaxyl4elakf0nbpt.png)
当前图形化界面属于 ROS2 应用层。各节点基于 ROS2 提供的 Node、Topic、TF 和 Launch 机制运行，其中 Topic 用于消息交换，TF 用于维护空间坐标关系，Launch 用于统一组织节点启动。应用层的发布订阅请求通过 RMW 接口下沉到具体中间件实现，在本实验中通常由 Fast DDS 基于 DDS/RTPS 完成底层发现与消息传输。
从功能视角看，ROS2 的 Topic 机制与 IoT 中常见的 MQTT 发布订阅模式存在一定相似性，DDS 的自动发现机制与 UPnP、mDNS 等设备发现机制也具有局部可比性。然而，ROS2 的 RMW 属于中间件抽象接口层，并不是网络协议；DDS 也不仅仅等同于某一种消息协议，而是同时承担发现、分发、QoS 与通信管理等多种职责。我们当前项目也只是理解ROS2内部的通讯机制，想要发展具身智能安全，还要深入跨主机，通过网络协议远程控制功能，或者VLA功能的项目。从而分析认证、伪造、注入、重放、拒绝服务这些安全问题。
## 通信伪造实验
从安全研究视角出发，本文设计了一个“主动控制消息链”小实验，用于验证机械臂姿态变化的本质驱动因素并非图形界面本身，而是 ROS2 系统中的消息链。已知在原始显示流程中，joint_state_publisher_gui 节点负责向 /joint_states 话题发布关节状态消息，robot_state_publisher 节点订阅该消息并结合机器人模型计算坐标变换，最终由 RViz 显示机械臂姿态。因此，如果能够伪造一个外部消息源，在不依赖 joint_state_publisher_gui 的情况下向 /joint_states 发布合法消息，并仍然影响机械臂姿态，就可以证明 ROS2 系统中的关键行为实际上是由消息链驱动的。这一结论可进一步延伸到后续研究，例如通过网络通信协议远程控制机器人运动状态的安全问题。
实验开始时，首先使用 ROS2 命令查看 /joint_states 对应消息类型的合法格式，并据此构造测试消息。随后使用如下命令持续向 /joint_states 发布关节状态：
```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 topic info /joint_states --no-daemon
ros2 topic echo /joint_states --no-daemon
```
通过 ros2 topic echo /joint_states --no-daemon 可以观察到系统持续输出关节状态消息，消息中包含 joint1 和 joint2 的名称及对应角度值，这表明关节状态消息链已经建立。从理论上看，此时外部节点已经能够向系统注入合法格式的关节控制信息。

![31.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditayaejsyo9ykgtdq.png)
再根据格式重新发包
```bash
ros2 topic pub /joint_states sensor_msgs/msg/JointState "{name: ['joint1', 'joint2'],
  position: [1.2, -0.6]}" -r 5
```
然而，进一步实验发现，在原始 GUI 启动模式下，虽然手动发布的 /joint_states 消息能够进入系统，但 RViz 中机械臂姿态并未立即发生明显变化。分析原因后发现，joint_state_publisher_gui 本身仍在持续向同一话题发布关节状态，因此手动注入的单次消息会很快被 GUI 后续发布的消息覆盖。也就是说，在同一话题存在多个发布者的情况下，最终系统表现由持续主导消息流的发布者决定。因此，如果希望准确验证“外部消息是否能够直接控制机械臂姿态”，就需要关闭 GUI 干扰，或采用更高频率的持续发布方式。
为此，实验进一步构建了一个不启动 GUI 的简化启动脚本，仅保留 robot_description_publisher、robot_state_publisher 和 rviz2。在该模式下，打开 RViz 后可观察到机械臂各连杆初始状态收缩在一起，仅显示坐标系。这一现象说明机器人模型描述已经加载，但由于系统尚未接收到有效的 /joint_states 输入，关节姿态尚未被展开。

![32.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditayk7syeqgw0mpce.png)
在此基础上，实验又补充实现了一个 joint_state_test_publisher 测试节点，用于模拟外部节点持续发布关节状态消息。该节点不依赖 joint_state_publisher_gui，而是直接构造合法的 sensor_msgs/msg/JointState 消息并发送到 /joint_states。随后再次使用 ros2 topic echo /joint_states --no-daemon 验证消息是否被正常发布和接收。通过这一方式，可以更稳定地证明：只要存在一个能够发布合法关节状态消息的外部节点，ROS2 系统中的机械臂姿态更新链路就能够被驱动。

![33.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditayncnj03palrnks.png)

![34.png](https://www.iotsec-zone.com/api/image/v2/20260527/ditayqw2lmk7depryh.png)
因此，该实验说明了一个重要事实：在 ROS2 机械臂显示系统中，图形界面并不是唯一控制源，真正决定系统行为的是关键话题上的消息输入。这为后续具身智能安全研究提供了直接启发，即如果攻击者能够伪造合法消息源、接入 ROS2 通信域并向关键控制话题持续发布数据，就有可能影响机器人状态表达，甚至进一步扩展到通过网络协议远程控制机器人运动姿态的安全场景。
