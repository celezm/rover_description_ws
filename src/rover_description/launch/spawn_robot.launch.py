import os
from os import environ, pathsep

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.descriptions import ParameterValue

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    description_file = LaunchConfiguration("description_file")
    use_sim_time = LaunchConfiguration("use_sim_time")

    gz_plugin_path = "/opt/ros/jazzy/lib"
    if "GZ_SIM_SYSTEM_PLUGIN_PATH" in environ:
        gz_plugin_path += pathsep + environ["GZ_SIM_SYSTEM_PLUGIN_PATH"]

    set_gz_plugin_path = SetEnvironmentVariable(
        name="GZ_SIM_SYSTEM_PLUGIN_PATH",
        value=gz_plugin_path
    )

    declare_description_file = DeclareLaunchArgument(
        "description_file",
        default_value="robot.urdf.xacro"
    )

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true"
    )

    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name="xacro")]),
        " ",
        PathJoinSubstitution([
            FindPackageShare("rover_description"),
            "robots",
            description_file
        ]),
    ])

    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str),
        "use_sim_time": use_sim_time,
    }

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    rviz_config = PathJoinSubstitution([
        FindPackageShare("rover_description"),
        "rviz",
        "robot.rviz"
    ])

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    gazebo_world = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("urjc_excavation_world"),
                "launch",
                "urjc_excavation_msr.launch.py"
            )
        )
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-name", "rover",
            "-topic", "/robot_description",
            "-x", "0",
            "-y", "0",
            "-z", "0.2",
        ],
    )

    return LaunchDescription([
        declare_description_file,
        declare_use_sim_time,
        set_gz_plugin_path, 
        robot_state_publisher,
        gazebo_world,
        spawn_robot,
        rviz,
    ])