import cv2
import h5py
import numpy as np
import os


def resize_frame(frame, size=(640, 360), is_top=False):
    """Resizes a frame to the given size."""
    if is_top:
        return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)

    return cv2.resize(frame, (240, 320), interpolation=cv2.INTER_AREA)


def extract_and_store_frames(
    video_path, hdf5_file, dataset_prefix, batch_size=100, is_top=True
):
    """Extracts frames from a given video, resizes them, and stores them in the HDF5 file."""
    cap = cv2.VideoCapture(video_path)
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
            dataset_name = f"{dataset_prefix}_{batch_count:04d}"
            while dataset_name in hdf5_file:
                batch_count += 1
                dataset_name = f"{dataset_prefix}_{batch_count:04d}"
            frames_array = np.array(frames_array, dtype=np.uint8)
            hdf5_file.create_dataset(
                dataset_name, data=frames_array, dtype=np.uint8, compression="gzip"
            )
            frames_array = []
            batch_count += 1

    if frames_array:
        dataset_name = f"{dataset_prefix}_{batch_count:04d}"
        while dataset_name in hdf5_file:
            batch_count += 1
            dataset_name = f"{dataset_prefix}_{batch_count:04d}"
        frames_array = np.array(frames_array, dtype=np.uint8)
        hdf5_file.create_dataset(
            dataset_name, data=frames_array, dtype=np.uint8, compression="gzip"
        )

    cap.release()


def process_videos_and_store(paths, output_dir, batch_size=100):
    """Processes videos from multiple directories and stores frames directly to HDF5 files in batches."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    hdf5_path = os.path.join(output_dir, "frames.hdf5")

    with h5py.File(hdf5_path, "w") as hdf5_file:
        for path in paths:
            for filename in os.listdir(path):
                if filename.endswith(".mp4"):
                    full_path = os.path.join(path, filename)
                    dataset_prefix = os.path.splitext(filename)[0]
                    print(f"Processing {full_path}...")
                    extract_and_store_frames(
                        full_path, hdf5_file, dataset_prefix, batch_size=batch_size
                    )

    print(f"Frames saved to {hdf5_path}")


# Example usage

# Example usage
video_paths = [
    "/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_push_1k/Ball/Single/20230811_1/robotCR17/Video",
    "/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_push_1k/Ball/Single/20230811_2/robotCR17/Video",
    "/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_push_1k/Ball/Single/20230811_3/robotCR17/Video",
    "/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_push_1k/Ball/Single/20230813_2/robotCR19/Video",
    "/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_push_1k/Ball/Single/20230815_1/robotCR19/Video",
    "/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_push_1k/Ball/Single/20230815_2/robotCR19/Video",
    "/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_push_1k/Ball/Single/20230815_3/robotCR19/Video",
]  # List of directories containing MP4 videos
hdf5_output_path = (
    "/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_push_1k/Ball/hdf5/"
)
process_videos_and_store(video_paths, hdf5_output_path)
