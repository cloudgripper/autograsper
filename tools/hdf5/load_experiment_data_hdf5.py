import os
import json
import h5py
import numpy as np

load_json = False


def load_experiment_data(experiment_id, start_frame, end_frame, base_path="hdf5"):
    """
    Load experiment data including video frames, states, and actions for a specified range of frames.

    Args:
        experiment_id (str): Identifier for the experiment.
        start_frame (int): The starting frame index for the data to be loaded.
        end_frame (int): The ending frame index for the data to be loaded.
        base_path (str, optional): Base directory path where HDF5 files are stored. Default is "hdf5".

    Returns:
        dict: A dictionary containing the following keys:
            - "bottom_frames" (list): List of frames from the bottom video corresponding to the specified frame range.
            - "normal_frames" (list): List of frames from the normal video corresponding to the specified frame range.
            - "states" (list): List of state dictionaries corresponding to the specified frame range.
            - "actions" (list): List of action dictionaries corresponding to the specified frame range.

    Example:
        data = load_experiment_data("203", 0, 100)
        bottom_frames = data["bottom_frames"]
        normal_frames = data["normal_frames"]
        states = data["states"]
        actions = data["actions"]
    """

    if load_json:
        hdf5_path = os.path.join(base_path, "frames.hdf5")
        experiment_path = os.path.join(base_path, str(experiment_id))
        task_path = os.path.join(experiment_path, "task")

        # Paths to states.json and actions.json
        states_path = os.path.join(task_path, "states.json")
        actions_path = os.path.join(task_path, "actions.json")

        # Load states.json
        with open(states_path, "r") as f:
            states = json.load(f)

        # Load actions.json
        with open(actions_path, "r") as f:
            actions = json.load(f)

        # Get relevant states and actions
        relevant_states = states[start_frame : end_frame + 1]
        relevant_actions = actions[start_frame : end_frame + 1]

    def load_frames_from_hdf5(hdf5_file, group_name, start_frame, end_frame):
        frames = []
        dataset_keys = sorted(
            [key for key in hdf5_file[group_name].keys() if key.endswith(".mp4")]
        )
        frame_count = 0

        for key in dataset_keys:
            dataset = hdf5_file[group_name][key]
            num_frames = dataset.shape[0]
            if frame_count + num_frames <= start_frame:
                frame_count += num_frames
                continue
            for i in range(num_frames):
                if start_frame <= frame_count <= end_frame:
                    frames.append(dataset[i])
                frame_count += 1
                if frame_count > end_frame:
                    break
            if frame_count > end_frame:
                break

        return frames

    # Open the HDF5 file
    with h5py.File(hdf5_path, "r") as hdf5_file:
        bottom_frames = load_frames_from_hdf5(
            hdf5_file, f"{experiment_id}/task_Bottom_Video", start_frame, end_frame
        )
        normal_frames = load_frames_from_hdf5(
            hdf5_file, f"{experiment_id}/task_Video", start_frame, end_frame
        )

    if load_json:
        return {
            "bottom_frames": bottom_frames,
            "normal_frames": normal_frames,
            "states": relevant_states,
            "actions": relevant_actions,
        }

    return {
        "bottom_frames": bottom_frames,
        "normal_frames": normal_frames,
    }


# Example usage
data = load_experiment_data("203", 0, 100)
bottom_frames = data["bottom_frames"]
normal_frames = data["normal_frames"]

if load_json:
    states = data["states"]
    actions = data["actions"]
