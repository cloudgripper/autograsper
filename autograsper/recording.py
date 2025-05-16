import os
import sys
import json
import logging
from typing import Any, Tuple, List, Dict, Optional
import cv2
import numpy as np
import threading

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from client.cloudgripper_client import GripperRobot
from library.utils import convert_ndarray_to_list, get_undistorted_bottom_image
from file_manager import FileManager

logger = logging.getLogger(__name__)


class Recorder:
    FOURCC = cv2.VideoWriter_fourcc(*"mp4v")

    def __init__(self, config: Any, output_dir: str, shutdown_event: threading.Event):
        self.shutdown_event = shutdown_event

        try:
            camera_config = config["camera"]
            experiment_config = config["experiment"]
            self.camera_matrix = np.array(camera_config["m"])
            self.distortion_coeffs = np.array(camera_config["d"])
            self.record_only_after_action = bool(
                camera_config["record_only_after_action"]
            )
            self.robot_idx = experiment_config["robot_idx"]
            self.save_data = bool(camera_config["record"])
            self.FPS = int(camera_config["fps"])
            self.save_images_individually = bool(
                camera_config["save_images_individually"]
            )
            self.clip_length = camera_config.get("clip_length", None)
        except KeyError as e:
            raise ValueError(f"Missing configuration key in Recorder: {e}") from e
        except TypeError as e:
            raise ValueError(f"Invalid configuration format in Recorder: {e}") from e

        self.token = os.getenv("CLOUDGRIPPER_TOKEN")
        if not self.token:
            raise ValueError("CLOUDGRIPPER_TOKEN environment variable not set")

        self.output_dir = output_dir
        self.robot = GripperRobot(self.robot_idx, self.token)

        self.image_top: Optional[np.ndarray] = None
        self.bottom_image: Optional[np.ndarray] = None
        self.pause = False

        # For when record_only_after_action is True.
        self.take_snapshot = 0

        # Reentrant locks for nested locking.
        self.image_lock = threading.RLock()
        self.writer_lock = threading.RLock()
        # Condition variable to synchronize snapshot requests.
        self.snapshot_cond = threading.Condition(threading.RLock())

        # State and writer variables.
        self.stop_flag = False
        self.frame_counter = 0
        self.video_counter = 0
        self.video_writer_top: Optional[cv2.VideoWriter] = None
        self.video_writer_bottom: Optional[cv2.VideoWriter] = None

        self._initialize_directories()

    def _initialize_directories(self) -> None:
        if self.save_images_individually:
            self.output_images_dir, self.output_bottom_images_dir = (
                FileManager.create_image_dirs(self.output_dir)
            )
        else:
            self.output_video_dir, self.output_bottom_video_dir = (
                FileManager.create_video_dirs(self.output_dir)
            )

    def _start_new_video(
        self,
    ) -> Tuple[Optional[cv2.VideoWriter], Optional[cv2.VideoWriter]]:
        if not self.ensure_images():
            return None, None

        video_filename_top = os.path.join(
            self.output_video_dir, f"video_{self.video_counter}.mp4"
        )
        video_filename_bottom = os.path.join(
            self.output_bottom_video_dir, f"video_{self.video_counter}.mp4"
        )

        with self.image_lock:
            top_shape = self.image_top.shape[1::-1]
            bottom_shape = self.bottom_image.shape[1::-1]
        video_writer_top = cv2.VideoWriter(
            video_filename_top, self.FOURCC, self.FPS, top_shape
        )
        video_writer_bottom = cv2.VideoWriter(
            video_filename_bottom, self.FOURCC, self.FPS, bottom_shape
        )
        return video_writer_top, video_writer_bottom

    def record(self) -> None:
        """Record video or images. Image display is handled externally."""
        self._prepare_new_recording()
        try:
            while not self.stop_flag and not self.shutdown_event.is_set():
                if not self.pause:
                    self._update()
                    if not self.ensure_images():
                        # Wait briefly for images to become available.
                        self.shutdown_event.wait(1 / self.FPS)
                        continue

                    if (not self.record_only_after_action) or (self.take_snapshot > 0):
                        if self.save_data:
                            self._capture_frame()
                        if (
                            self.clip_length
                            and (self.frame_counter % self.clip_length == 0)
                            and (self.frame_counter != 0)
                            and not self.save_images_individually
                        ):
                            self.video_counter += 1
                            self._start_or_restart_video_writers()
                        # Use shutdown_event.wait to allow prompt shutdown.
                        self.shutdown_event.wait(1 / self.FPS)
                        if self.save_data:
                            self.save_state()
                        self.frame_counter += 1
                    else:
                        self.shutdown_event.wait(1 / self.FPS)
                else:
                    self.shutdown_event.wait(1 / self.FPS)
        except Exception as e:
            logger.exception("An error occurred in Recorder.record:", e)
            self.shutdown_event.set()
        finally:
            self._release_writers()

    def _update(self) -> None:
        """Update image and state data from the robot."""
        try:
            data = self.robot.get_all_states()
            with self.image_lock:
                self.image_top = data[0]
                self.bottom_image = get_undistorted_bottom_image(
                    self.robot, self.camera_matrix, self.distortion_coeffs
                )
            self.state = data[2]
            self.timestamp = data[3]
        except Exception as e:
            logger.exception("Error updating images/state:", e)
            raise

    def _capture_frame(self) -> None:
        """Capture and save the current frame as an image or add it to the video writer."""
        try:
            if not self.ensure_images():
                return
            with self.image_lock:
                top_image = self.image_top.copy()
                bottom_image = self.bottom_image.copy()
            if self.save_images_individually:
                self._save_individual_images(top_image, bottom_image)
            else:
                with self.writer_lock:
                    if (
                        self.video_writer_top is not None
                        and self.video_writer_bottom is not None
                    ):
                        self.video_writer_top.write(top_image)
                        self.video_writer_bottom.write(bottom_image)
                    else:
                        logger.warning("Video writers not initialized.")
        except Exception as e:
            logger.exception("Error capturing frame:", e)
        finally:
            with self.snapshot_cond:
                if self.take_snapshot > 0:
                    self.take_snapshot -= 1
                    if self.take_snapshot == 0:
                        self.snapshot_cond.notify_all()

    def _save_individual_images(
        self, top_image: np.ndarray, bottom_image: np.ndarray
    ) -> None:
        """Save the top and bottom images as individual JPEG files."""
        try:
            top_filename = os.path.join(
                self.output_images_dir, f"image_top_{self.frame_counter}.jpeg"
            )
            bottom_filename = os.path.join(
                self.output_bottom_images_dir, f"image_bottom_{self.frame_counter}.jpeg"
            )
            cv2.imwrite(top_filename, top_image)
            cv2.imwrite(bottom_filename, bottom_image)
        except Exception as e:
            logger.exception("Error saving individual images:", e)

    def _start_or_restart_video_writers(self) -> None:
        """Restart the video writers if not saving images individually."""
        if not self.save_images_individually:
            with self.writer_lock:
                self._release_writers()
                self.video_writer_top, self.video_writer_bottom = (
                    self._start_new_video()
                )

    def _release_writers(self) -> None:
        """Release the video writers if they have been initialized."""
        with self.writer_lock:
            if self.video_writer_top:
                self.video_writer_top.release()
                self.video_writer_top = None
            if self.video_writer_bottom:
                self.video_writer_bottom.release()
                self.video_writer_bottom = None

    def start_new_recording(self, new_output_dir: str) -> None:
        """Start a new recording session in the specified directory."""
        self.output_dir = new_output_dir
        self._initialize_directories()
        self._prepare_new_recording()
        logger.info("Started new recording in directory: %s", new_output_dir)

    def _prepare_new_recording(self) -> None:
        """Prepare for a new recording session."""
        self.stop_flag = False
        if not self.save_images_individually:
            self._start_or_restart_video_writers()

    def stop(self) -> None:
        """Stop the recorder."""
        self.stop_flag = True
        logger.info("Stop flag set to True in Recorder")

    def save_state(self) -> None:
        """Save the current state to a JSON file."""
        try:
            state = self.state.copy() if isinstance(self.state, dict) else self.state
            timestamp = self.timestamp
            state = convert_ndarray_to_list(state)
            if not isinstance(state, dict):
                state = {"state": state}
            state["time"] = timestamp

            state_file = os.path.join(self.output_dir, "states.json")
            data: List[Dict[str, Any]] = []
            if os.path.exists(state_file):
                with open(state_file, "r") as file:
                    data = json.load(file)
            data.append(state)
            with open(state_file, "w") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            logger.exception("Error saving state:", e)

    def ensure_images(self) -> bool:
        """Ensure that valid images are available. Try updating if not."""
        with self.image_lock:
            if self.image_top is None or self.bottom_image is None:
                self._update()
            if self.image_top is None or self.bottom_image is None:
                logger.error(
                    "ensure_images: Failed to obtain valid images from the robot after update."
                )
                return False
        return True
