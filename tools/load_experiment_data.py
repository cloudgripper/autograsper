import os
import os
import json
import cv2
import numpy as np


def load_experiment_data(
    experiment_id, base_path="path_to_experiments"
):
    """
    Load experiment data including video frames, states, and actions for a specified range of frames.

    Args:
        experiment_id (str): Identifier for the experiment.
        base_path (str, optional): Base directory path where experiments are stored. Default is "path_to_experiments".

    Returns:
        dict: A dictionary containing the following keys:
            - "bottom_frames" (list): List of frames from the bottom video corresponding to the specified frame range.
            - "normal_frames" (list): List of frames from the normal video corresponding to the specified frame range.
            - "states_actions" (list): List of state dictionaries corresponding to the specified frame range.

    Example:
        data = load_experiment_data("experiment_001", 0, 100)
        bottom_frames = data["bottom_frames"]
        normal_frames = data["normal_frames"]
        states_actions = data["states_actions"]
    """

    experiment_path = os.path.join(base_path, str(experiment_id))
   
    if not os.path.exists(experiment_path):
        print(f"Experiment path {experiment_path} does not exist. Skipping.")
        return
    
    task_path = os.path.join(experiment_path, "task")

    # Paths to video directories
    bottom_video_path = os.path.join(task_path, "extracted_states_bottom_video.mp4")
    normal_video_path = os.path.join(task_path, "extracted_states_video.mp4")

    # # Path to states and actions
    state_action_path = os.path.join(task_path, "extracted_combined.json")
    
    # Task status: success or failure
    status_path = os.path.join(experiment_path, "status.txt")
    
    with open(status_path, "r") as f:
        status = f.read().strip()

    with open(state_action_path, "r") as f:
        states_actions = json.load(f)

    # Function to load frames from videos
    def load_frames_from_videos(video_file_path):
        frames = []
        frame_count = 0

        if not os.path.isfile(video_file_path):
            print(f"Error: {video_file_path} is not a valid file")
            return frames

        cap = cv2.VideoCapture(video_file_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file {video_file_path}")
            return frames

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            frame_count += 1

        cap.release()
        return frames

    # Load frames from Bottom_Video
    bottom_frames = load_frames_from_videos(bottom_video_path)

    # Load frames from Video
    normal_frames = load_frames_from_videos(normal_video_path)

    return {
        "bottom_frames": bottom_frames,
        "normal_frames": normal_frames,
        "states_actions": states_actions,
        "status": status
    }
