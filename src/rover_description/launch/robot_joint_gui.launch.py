from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():

    moveit_config = MoveItConfigsBuilder(
        "rover",
        package_name="rover_moveit_config"
    ).to_moveit_configs()

    declare_sim_time = DeclareLaunchArgument(
        "use_sim_time",
        default_value="false",
        description="Use simulation time"
    )

    robot_description_launcher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("rover_moveit_config"),
                    "launch",
                    "rsp.launch.py",
                ]
            )
        ),
        launch_arguments={
            "use_sim_time": LaunchConfiguration("use_sim_time"),
        }.items(),
    )

    rviz_config_file = PathJoinSubstitution(
        [
            FindPackageShare("rover_description"),
            "rviz",
            "robot.rviz",
        ]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_file],
        parameters=[
            {
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            }
        ],
    )

    joint_state_publisher_gui_node = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        name="joint_state_publisher_gui",
        output="screen",
        parameters=[
            moveit_config.robot_description,
            {
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            },
        ],
    )

    ld = LaunchDescription()

    ld.add_action(declare_sim_time)
    ld.add_action(robot_description_launcher)
    ld.add_action(joint_state_publisher_gui_node)
    ld.add_action(rviz_node)

    return ld