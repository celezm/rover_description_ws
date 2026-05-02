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

    # 1. Gazebo arranca inmediatamente con el mundo
    gazebo_world = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("urjc_excavation_world"),
                "launch",
                "urjc_excavation_msr.launch.py"
            )
        )
    )

    # 2. Spawn del robot usando -string (NO publica en /robot_description)
    #    Espera 5s a que Gazebo cargue el mundo y el plugin gz_ros2_control
    #    esté listo para recibir el robot en el EntityComponentManager
    spawn_robot = TimerAction(
        period=5.0,
        actions=[
            Node(
                package="ros_gz_sim",
                executable="create",
                output="screen",
                arguments=[
                    "-name", "rover",
                    "-string", robot_description_content,  # directo, sin topic
                    "-x", "0",
                    "-y", "0",
                    "-z", "0.2",
                ],
            )
        ]
    )

    return LaunchDescription([
        declare_description_file,
        declare_use_sim_time,
        SetEnvironmentVariable(name="GZ_SIM_SYSTEM_PLUGIN_PATH", value=gz_plugin_path),
        gazebo_world,   # t=0s  Gazebo + mundo + gz_ros2_control
        spawn_robot,    # t=5s  robot spawnado con URDF directo
        # SIN robot_state_publisher → lo lanzas tú después con el launch 2
    ])