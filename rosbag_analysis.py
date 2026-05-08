#!/usr/bin/env python3

import argparse
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from rclpy.serialization import deserialize_message
from rosbag2_py import ConverterOptions, SequentialReader, StorageOptions
from rosidl_runtime_py.utilities import get_message


TOPICS = {"/cmd_vel", "/imu", "/joint_states"}
SCARA_TOKENS = ("arm", "clamp", "gripper")


def get_storage_id(bag_path):
    files = os.listdir(bag_path)
    if any(name.endswith(".mcap") for name in files):
        return "mcap"
    if any(name.endswith(".db3") for name in files):
        return "sqlite3"
    raise RuntimeError("Could not find rosbag storage file (.mcap or .db3)")

# These functions check if it is a token from the rover (wheel or scara)
def joint_matches(name, tokens):
    name_lower = name.lower()
    return any(token in name_lower for token in tokens)

def is_wheel_joint(name):
    name_lower = name.lower()
    return "wheel" in name_lower


def is_scara_joint(name):
    return joint_matches(name, SCARA_TOKENS)


def seconds_from_start(timestamp, start_timestamp):
    return (timestamp - start_timestamp) * 1e-9

# Reads rosbag and saves data from each topic
def read_ros2_bag(bag_path):
    reader = SequentialReader()
    reader.open(
        StorageOptions(uri=bag_path, storage_id=get_storage_id(bag_path)),
        ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr"),
    )

    type_map = {topic.name: topic.type for topic in reader.get_all_topics_and_types()}
    missing = sorted(TOPICS - set(type_map))
    if missing:
        print(f"Missing topics: {', '.join(missing)}")

    msg_types = {
        topic: get_message(msg_type)
        for topic, msg_type in type_map.items()
        if topic in TOPICS
    }

    data = {
        "wheel_time": [],
        "wheel_pos": defaultdict(list),
        "wheel_effort": defaultdict(list),

        "scara_time": [],
        "scara_effort": defaultdict(list),

        "imu_time": [],
        "acc_x": [],
        "acc_y": [],
        "acc_z": [],
        "acc_mod": [],

        "cmd_time": [],
        "cmd_gasto": [],
    }

    start_timestamp = None

    while reader.has_next():
        topic, raw_data, timestamp = reader.read_next()

        if topic not in TOPICS:
            continue

        if start_timestamp is None:
            start_timestamp = timestamp

        time_s = seconds_from_start(timestamp, start_timestamp)
        msg = deserialize_message(raw_data, msg_types[topic])

        if topic == "/joint_states":
            read_joint_states_msg(data, msg, time_s)
        elif topic == "/imu":
            read_imu_msg(data, msg, time_s)
        elif topic == "/cmd_vel":
            read_cmd_vel_msg(data, msg, time_s)

    data["wheel_pos"] = dict(data["wheel_pos"])
    data["wheel_effort"] = dict(data["wheel_effort"])
    data["scara_effort"] = dict(data["scara_effort"])

    return data


def append_joint_group(time_list, effort_dict, msg, indexes, time_s):
    if not indexes:
        return

    time_list.append(time_s)
    present_joints = {name for _, name in indexes}

    for name in effort_dict:
        if name not in present_joints:
            effort_dict[name].append(np.nan)

    for index, name in indexes:
        if name not in effort_dict:
            effort_dict[name] = [np.nan] * (len(time_list) - 1)

        effort = msg.effort[index] if index < len(msg.effort) else np.nan
        effort_dict[name].append(effort)


def read_joint_states_msg(data, msg, time_s):
    wheel_indexes = [
        (index, name)
        for index, name in enumerate(msg.name)
        if is_wheel_joint(name)
    ]

    scara_indexes = [
        (index, name)
        for index, name in enumerate(msg.name)
        if is_scara_joint(name)
    ]

    if wheel_indexes:
        data["wheel_time"].append(time_s)
        present_wheels = {name for _, name in wheel_indexes}

        for name in data["wheel_pos"]:
            if name not in present_wheels:
                data["wheel_pos"][name].append(np.nan)
                data["wheel_effort"][name].append(np.nan)

        for index, name in wheel_indexes:
            if name not in data["wheel_pos"]:
                data["wheel_pos"][name] = [np.nan] * (len(data["wheel_time"]) - 1)
                data["wheel_effort"][name] = [np.nan] * (len(data["wheel_time"]) - 1)

            position = msg.position[index] if index < len(msg.position) else np.nan
            effort = msg.effort[index] if index < len(msg.effort) else np.nan

            data["wheel_pos"][name].append(position)
            data["wheel_effort"][name].append(effort)

    append_joint_group(
        data["scara_time"],
        data["scara_effort"],
        msg,
        scara_indexes,
        time_s,
    )


def read_imu_msg(data, msg, time_s):
    ax = msg.linear_acceleration.x
    ay = msg.linear_acceleration.y
    az = msg.linear_acceleration.z

    data["imu_time"].append(time_s)
    data["acc_x"].append(ax)
    data["acc_y"].append(ay)
    data["acc_z"].append(az)
    data["acc_mod"].append(float(np.sqrt(ax**2 + ay**2 + az**2)))


def read_cmd_vel_msg(data, msg, time_s):
    linear = msg.linear.x
    angular = msg.angular.z

    data["cmd_time"].append(time_s)
    data["cmd_gasto"].append(abs(linear) + abs(angular))


def setup_axes(title, xlabel, ylabel):
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.35)


def save_plot(output_dir, filename):
    plt.tight_layout()
    output_path = os.path.join(output_dir, filename)
    plt.savefig(output_path, dpi=160)
    plt.close()
    print(f"Saved in: {output_path}")


def effort_is_available(effort_dict):
    for efforts in effort_dict.values():
        values = np.asarray(efforts, dtype=float)
        if values.size and np.isfinite(values).any():
            return True
    return False


def calculate_gasto(effort_dict):
    if not effort_dict:
        return np.array([])

    effort_matrix = np.array(
        [effort_dict[name] for name in sorted(effort_dict)],
        dtype=float,
    )

    return np.nansum(np.abs(effort_matrix), axis=0)


def plot_wheel_positions(data, output_dir):
    plt.figure(figsize=(11, 6))

    for joint_name in sorted(data["wheel_pos"]):
        plt.plot(
            data["wheel_time"],
            data["wheel_pos"][joint_name],
            label=joint_name,
        )

    setup_axes(
        "Posicion de las ruedas vs tiempo",
        "Tiempo [s]",
        "Posicion [rad]",
    )

    if data["wheel_pos"]:
        plt.legend(loc="best", fontsize="small")
    else:
        print("Not wheel joints in /joint_states")

    save_plot(output_dir, "posicion_ruedas_vs_tiempo.png")


def plot_acceleration(data, output_dir):
    plt.figure(figsize=(11, 6))

    if data["imu_time"]:
        plt.plot(data["imu_time"], data["acc_x"], label="ax")
        plt.plot(data["imu_time"], data["acc_y"], label="ay")
        plt.plot(data["imu_time"], data["acc_z"], label="az")
        plt.plot(data["imu_time"], data["acc_mod"], label="|a|", linewidth=2)
        plt.legend(loc="best")
    else:
        print("Not messages in /imu")

    setup_axes(
        "Aceleracion vs tiempo",
        "Tiempo [s]",
        "Aceleracion [m/s^2]",
    )

    save_plot(output_dir, "aceleracion_vs_tiempo.png")


def plot_gasto_ruedas(data, output_dir):
    plt.figure(figsize=(11, 6))

    if effort_is_available(data["wheel_effort"]):
        gasto_ruedas = calculate_gasto(data["wheel_effort"])

        plt.plot(
            data["wheel_time"],
            gasto_ruedas,
            label="Gasto ruedas: suma |effort ruedas|",
            linewidth=2,
        )
    else:
        print("Not wheels' effort in /joint_states")

    setup_axes(
        "Gasto ruedas vs tiempo",
        "Tiempo [s]",
        "Gasto ruedas [suma |effort|]",
    )

    if plt.gca().has_data():
        plt.legend(loc="best")

    save_plot(output_dir, "gasto_ruedas_vs_tiempo.png")


def plot_gasto_scara(data, output_dir):
    plt.figure(figsize=(11, 6))

    if effort_is_available(data["scara_effort"]):
        gasto_scara = calculate_gasto(data["scara_effort"])

        plt.plot(
            data["scara_time"],
            gasto_scara,
            label="Gasto SCARA: suma |effort SCARA|",
            linewidth=2,
        )
    else:
        print("No SCARA info in /joint_states")

    setup_axes(
        "Gasto SCARA vs tiempo",
        "Tiempo [s]",
        "Gasto SCARA [suma |effort|]",
    )

    if plt.gca().has_data():
        plt.legend(loc="best")

    save_plot(output_dir, "gasto_scara_vs_tiempo.png")


def plot_gasto_total(data, output_dir):
    plt.figure(figsize=(11, 6))

    has_wheels = effort_is_available(data["wheel_effort"])
    has_scara = effort_is_available(data["scara_effort"])

    if not has_wheels and not has_scara:
        print("Could not obtain total cost")
        setup_axes(
            "Gasto total vs tiempo",
            "Tiempo [s]",
            "Gasto total [suma |effort|]",
        )
        save_plot(output_dir, "gasto_total_vs_tiempo.png")
        return

    curves = []

    if has_wheels:
        gasto_ruedas = calculate_gasto(data["wheel_effort"])
        curves.append((np.array(data["wheel_time"]), gasto_ruedas))

    if has_scara:
        gasto_scara = calculate_gasto(data["scara_effort"])
        curves.append((np.array(data["scara_time"]), gasto_scara))

    common_time = sorted(set(np.concatenate([curve[0] for curve in curves])))

    gasto_total = np.zeros(len(common_time))

    for time_array, gasto_array in curves:
        interpolated = np.interp(
            common_time,
            time_array,
            gasto_array,
            left=0.0,
            right=0.0,
        )
        gasto_total += interpolated

    plt.plot(
        common_time,
        gasto_total,
        label="Gasto total: ruedas + SCARA",
        linewidth=2,
    )

    setup_axes(
        "Gasto total vs tiempo",
        "Tiempo [s]",
        "Gasto total [suma |effort|]",
    )

    plt.legend(loc="best")
    save_plot(output_dir, "gasto_total_vs_tiempo.png")


def print_summary(data):
    print("\nData")
    print("----------------------------")
    print(f"Wheels in /joint_states: {len(data['wheel_time'])}")
    print(f"Wheels : {', '.join(sorted(data['wheel_pos'])) or 'nothing'}")
    print(f"SCARA in /joint_states: {len(data['scara_time'])}")
    print(f"Joints SCARA: {', '.join(sorted(data['scara_effort'])) or 'nothing'}")
    print(f"/imu data: {len(data['imu_time'])}")
    print(f"/cmd_vel data : {len(data['cmd_time'])}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analysis of the /cdm_vel, /imu and /joint_states topics"
    )

    parser.add_argument(
        "bag_path",
        nargs="?",
        default="practicafinal",
        help="Default: practicafinal",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        default="graficas",
        help="Default: graficas",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.isdir(args.bag_path):
        raise SystemExit(f"Error: '{args.bag_path}' is not a rosbag")

    os.makedirs(args.output_dir, exist_ok=True)

    data = read_ros2_bag(args.bag_path)
    print_summary(data)

    plot_wheel_positions(data, args.output_dir)
    plot_acceleration(data, args.output_dir)
    plot_gasto_ruedas(data, args.output_dir)
    plot_gasto_scara(data, args.output_dir)
    plot_gasto_total(data, args.output_dir)

    print(f"\nGraphs saved in: {args.output_dir}")


if __name__ == "__main__":
    main()