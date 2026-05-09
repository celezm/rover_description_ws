from os.path import join

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction

from ament_index_python.packages import get_package_share_directory
from controller_manager.launch_utils import generate_load_controller_launch_description


def generate_launch_description():

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="use_sim_time simulation parameter"
    )

    pkg_share_folder = get_package_share_directory("rover_description")
    controllers_file = join(pkg_share_folder, "config", "robot_controllers.yaml")

    joint_state_broadcaster = GroupAction([
        generate_load_controller_launch_description(
            controller_name="joint_state_broadcaster",
            controller_params_file=controllers_file
        )
    ])

    base_controller = GroupAction([
        generate_load_controller_launch_description(
            controller_name="rover_base_control",
            controller_params_file=controllers_file
        )
    ])

    arm_controller = GroupAction([
        generate_load_controller_launch_description(
            controller_name="scara_controller",
            controller_params_file=controllers_file
        )
    ])

    gripper_controller = GroupAction([
        generate_load_controller_launch_description(
            controller_name="gripper_controller",
            controller_params_file=controllers_file
        )
    ])

    return LaunchDescription([
        declare_use_sim_time,
        joint_state_broadcaster,
        base_controller,
        arm_controller,
        gripper_controller
    ])
