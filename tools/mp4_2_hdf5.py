import cv2
import h5py
import numpy as np
import os
import threading
from concurrent.futures import ThreadPoolExecutor


def resize_frame(frame, size=(640, 360), is_top=False):
    """Resizes a frame to the given size."""
    if is_top:
        return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
    return cv2.resize(frame, (240, 320), interpolation=cv2.INTER_AREA)


def process_frame_and_store(
    cap, hdf5_group, video_filename, batch_size=100, is_top=True
):
    """Processes frames from a video capture object and stores them in the HDF5 group."""
    frame_count = 0
    batch_count = 0
    frames_array = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        resized_frame = resize_frame(frame, is_top=is_top)
        frames_array.append(resized_frame)
        frame_count += 1

        if frame_count % batch_size == 0:
            dataset_name = f"{video_filename}_{batch_count:04d}"
            frames_array = np.array(frames_array, dtype=np.uint8)
            with hdf5_file_lock:
                hdf5_group.create_dataset(
                    dataset_name, data=frames_array, dtype=np.uint8, compression="gzip"
                )
            frames_array = []
            batch_count += 1

    if frames_array:
        dataset_name = f"{video_filename}_{batch_count:04d}"
        frames_array = np.array(frames_array, dtype=np.uint8)
        with hdf5_file_lock:
            hdf5_group.create_dataset(
                dataset_name, data=frames_array, dtype=np.uint8, compression="gzip"
            )


def process_single_video(video_path, hdf5_group, batch_size, is_top):
    """Helper function to process a single video."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Failed to open {video_path}")
        return

    video_filename = os.path.splitext(os.path.basename(video_path))[0]
    process_frame_and_store(cap, hdf5_group, video_filename, batch_size, is_top)
    cap.release()
    print(f"Finished processing {video_path}")


def process_videos_and_store(
    video_ids,
    base_path,
    path_suffixes,
    output_dir,
    batch_size=100,
    max_workers=4,
    is_top=True,
):
    """Processes videos from multiple directories and stores frames in a single HDF5 file grouped by video ID."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    hdf5_path = os.path.join(output_dir, "frames.hdf5")

    with h5py.File(hdf5_path, "w") as hdf5_file:
        global hdf5_file_lock
        hdf5_file_lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for video_id in video_ids:
                video_group = hdf5_file.create_group(video_id)
                for suffix in path_suffixes:
                    suffix_group_name = suffix.replace("/", "_")
                    suffix_group = video_group.create_group(suffix_group_name)
                    video_path = os.path.join(base_path, video_id, suffix)
                    if os.path.exists(video_path):
                        filenames = sorted(
                            [f for f in os.listdir(video_path) if f.endswith(".mp4")]
                        )
                        for filename in filenames:
                            if filename.endswith(".mp4"):
                                full_path = os.path.join(video_path, filename)
                                executor.submit(
                                    process_single_video,
                                    full_path,
                                    suffix_group,
                                    batch_size,
                                    is_top,
                                )

    print(f"Frames saved to {hdf5_path}")


# Define the directory prefix and suffixes
# path to Berzelius dataset
path_prefix = (
    "/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_push_1k/Ball/Single/"
)

# Multiple suffixes
# You can add path to bottom video to convert that as well
path_suffixes = [
    "robotCR17/Video",
]

# Example usage
# You add more video IDs
video_ids = [
    "20230811_1",
]  # List of video IDs

# Define the output directory for the HDF5 file
hdf5_output_path = "hdf5/"

# Process the videos and store frames in the HDF5 file
process_videos_and_store(
    video_ids,
    path_prefix,
    path_suffixes,
    hdf5_output_path,
    batch_size=100,
    max_workers=4,
)
