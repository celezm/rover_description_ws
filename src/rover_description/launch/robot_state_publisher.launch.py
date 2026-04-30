from launch import LaunchDescription
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.descriptions import ParameterValue

import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import LaunchConfiguration
from launch.actions import ExecuteProcess
from launch.actions import SetEnvironmentVariable
import os

def generate_launch_description():
    description_file = LaunchConfiguration("description_file", default="robot.urdf.xacro")
    use_sim_time = LaunchConfiguration("use_sim_time", default="false")

    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name="xacro")]),
        " ",
        PathJoinSubstitution([
            FindPackageShare("rover_description"),
            "robots",
            description_file
        ]),
    ])

    rviz_config = PathJoinSubstitution([
        FindPackageShare("rover_description"),
        "rviz",
        "robot.rviz"
    ])

    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str),
        "use_sim_time": use_sim_time,
    }

    joint_state_publisher_node = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        name="joint_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
    )

    urjc_excavation = launch.actions.IncludeLaunchDescription(
    launch.launch_description_sources.PythonLaunchDescriptionSource(
        os.path.join(
            get_package_share_directory('urjc_excavation_world'),
            'launch',
            'urjc_excavation.launch.py')))
    
    # Spawning robot
    gazebo_spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-model", "rover",
            "-topic", "robot_description",
            "-use_sim_time", "True",
        ],
    )

    return LaunchDescription([
        joint_state_publisher_node,
        robot_state_publisher_node,
        rviz_node,
        urjc_excavation,
        gazebo_spawn_robot
    ])