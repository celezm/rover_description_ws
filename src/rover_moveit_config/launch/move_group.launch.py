from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder("rover", package_name="rover_moveit_config").to_moveit_configs()
    moveit_config.trajectory_execution["trajectory_execution.allowed_start_tolerance"] = 0.12
    moveit_config.planning_pipelines["start_state_max_bounds_error"] = 0.5
    return generate_move_group_launch(moveit_config)
