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
        for idx in range(len(traj)):
            in_obs, in_ac, in_reward = traj[idx][0], traj[idx][1], traj[idx][2]
            out_obs = {
                "state": np.array(in_obs["state"]).astype(np.float32),
                "enc_cam_0": _resize_and_encode(in_obs["image"]),
            }
            out_action = np.array(in_ac).astype(np.float32)
            out_reward = float(in_reward)
            out_traj.append((out_obs, out_action, out_reward))
        out_buffer.append(out_traj)

    with open(os.path.join(out_path, "stage_1_50epi.pkl"), "wb") as f:
        pkl.dump(out_buffer, f)

def populate_input_trajs(
    start_experiment, end_experiment, base_path, num_frames
):
    input_trajs = []

    for experiment_id in range(start_experiment, end_experiment + 1):
        experiment_data = load_experiment_data(
            experiment_id, base_path
        )
        if experiment_data:
            normal_frames = experiment_data["normal_frames"]
            states_actions = experiment_data["states_actions"]
            status = experiment_data["status"]
            traj = []
            if len(normal_frames)==num_frames and status=="success":    
            # if status=="success":    

                for i in range(len(normal_frames)):
                    image = normal_frames[i]
                    state_action = states_actions[i]

                    state_values = [
                        state_action["x_norm"],
                        state_action["y_norm"],
                        state_action["z_norm"],
                        state_action["rotation"],
                        state_action["claw_norm"],
                    ]

                    action_values = [
                        state_action["order"]["x_norm"],
                        state_action["order"]["y_norm"],
                        state_action["order"]["z_norm"],
                        state_action["order"]["rotation"],
                        state_action["order"]["claw_norm"],
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
                input_trajs.append(traj)
                print("number of successful trajectories:", len(input_trajs))
            else:
                print(experiment_id, " has ", len(normal_frames), "  frames", ", should be 4")

    return input_trajs


if __name__ == "__main__":
    start_experiment = 457
    end_experiment = 565
    num_frames= 4
    base_path =  "/proj/cloudrobotics-nest/users/Stacking/dataset/Random_Grasping/stage_1_new_collection"

    input_trajs = populate_input_trajs(
        start_experiment, end_experiment, base_path, num_frames
    )

    out_path = "/proj/cloudrobotics-nest/users/Stacking/dataset/Random_Grasping"
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    convert_trajectories(input_trajs, out_path)
