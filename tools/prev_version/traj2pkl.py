import cv2
import numpy as np
import pickle as pkl
import os
from tqdm import tqdm

from load_experiment_data import load_experiment_data


def _resize_and_encode(rgb_img, size=(256, 256)):
    bgr_image = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)
    bgr_image = cv2.resize(bgr_image, size, interpolation=cv2.INTER_AREA)
    _, encoded = cv2.imencode(".jpg", bgr_image)
    return encoded


def convert_trajectories(input_trajs, out_path):
    out_buffer = []
    for traj in tqdm(input_trajs):
        out_traj = []
        
        # for in_obs, in_ac, in_reward in traj:
        in_obs, in_ac, in_reward = traj[0], traj[1], traj[2]
        out_obs = {
            "state": np.array(in_obs["state"]).astype(np.float32),
            "enc_cam_0": _resize_and_encode(in_obs["image"]),
        }
        out_action = np.array(in_ac).astype(np.float32)
        out_reward = float(in_reward)
        out_traj.append((out_obs, out_action, out_reward))
        out_buffer.append(out_traj)

    with open(os.path.join(out_path, "example.pkl"), "wb") as f:
        pkl.dump(out_buffer, f)


def populate_input_trajs(
    start_experiment, end_experiment, start_frame, end_frame, base_path
):
    input_trajs = []

    for experiment_id in range(start_experiment, end_experiment + 1):
        experiment_data = load_experiment_data(
            experiment_id, start_frame, end_frame, base_path
        )
        normal_frames = experiment_data["normal_frames"]
        states = experiment_data["states"]
        actions = experiment_data["actions"]
        # print(len(actions))
        traj = []
        for i in range(len(normal_frames)):
            state = states[i]
            action = actions[i]
            image = normal_frames[i]

            state_values = [
                state["x_norm"],
                state["y_norm"],
                state["z_norm"],
                state["claw_norm"],
                state["rotation"],
            ]

            action_values = [
                action["x_norm_diff"],
                action["y_norm_diff"],
                action["z_norm_diff"],
                action["claw_norm_diff"],
                action["rotation_diff"]
            ]

            traj_data = (
                {
                    'state': state_values,
                    'image': image
                },
                action_values,
                0
            )
            traj.append(traj_data)
        input_trajs.append(traj_data)

    return input_trajs


if __name__ == "__main__":
    start_experiment = 1
    end_experiment = 205
    start_frame = 0
    end_frame = 15
    base_path =  "/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_stack_1k/limited_pos"

    input_trajs = populate_input_trajs(
        start_experiment, end_experiment, start_frame, end_frame, base_path
    )

    out_path = "../"
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    convert_trajectories(input_trajs, out_path)
