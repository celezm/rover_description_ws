import os
from os import environ, pathsep

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription,
    SetEnvironmentVariable, TimerAction
)
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

    declare_description_file = DeclareLaunchArgument(
        "description_file",
        default_value="robot.urdf.xacro"
    )

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true"
    )

    # Genera el URDF expandido para pasarlo directamente al spawn con -string
    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name="xacro")]),
        " ",
        PathJoinSubstitution([
            FindPackageShare("rover_description"),
            "robots",
            description_file
        ]),
        " config_controllers:=",
        PathJoinSubstitution([
            FindPackageShare("rover_description"),
            "config",
            "robot_controllers.yaml"
        ]),
    ])

    gazebo_world = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("urjc_excavation_world"),
                "launch",
                "urjc_excavation_msr.launch.py"
            )
        )
    )

    spawn_robot = TimerAction(
        period=5.0,
        actions=[
            Node(
                package="ros_gz_sim",
                executable="create",
                output="screen",
                arguments=[
                    "-name", "rover",
                    "-string", robot_description_content,
                    "-x", "0",
                    "-y", "0",
                    "-z", "0.2",
                ],
            )
        ]
    )

    twist_stamped = Node(
        package="twist_stamper",
        executable="twist_stamper",
        name="twist_stamper",
        output="screen",
        parameters=[
            {
                "use_sim_time": True,
            }
        ],
        remappings=[
            ("cmd_vel_out", "/rover_base_control/cmd_vel"),
            ("cmd_vel_in", "/cmd_vel"),
        ],
    )

    imu_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="imu_bridge",
        output="screen",
        arguments=[
            "/imu@sensor_msgs/msg/Imu@gz.msgs.IMU",
        ],
        parameters=[
            {
                "use_sim_time": use_sim_time,
            }
        ],
    )

    return LaunchDescription([
        declare_description_file,
        declare_use_sim_time,
        SetEnvironmentVariable(name="GZ_SIM_SYSTEM_PLUGIN_PATH", value=gz_plugin_path),
        gazebo_world,   # t=0s  Gazebo + mundo + gz_ros2_control
        spawn_robot,    # t=5s  robot spawnado con URDF directo
        twist_stamped,
        imu_bridge
        # SIN robot_state_publisher → lo lanzas tú después con el launch 2
    ])
