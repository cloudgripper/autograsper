# coordinator.py
import os
import logging
import time
import concurrent.futures
import threading
from dataclasses import dataclass
from queue import Queue, Empty

from grasper import RobotActivity, AutograsperBase
from recording import Recorder
from file_manager import FileManager

logger = logging.getLogger(__name__)


@dataclass
class SharedState:
    """
    Holds shared references between threads.
    """

    state: str = RobotActivity.STARTUP
    recorder: Recorder = None


class DataCollectionCoordinator:
    """
    Orchestrates the autograsper, manages recording, and coordinates state changes
    and image updates via a centralized message queue.
    """

    def __init__(
        self, config, grasper: AutograsperBase, shutdown_event: threading.Event
    ):
        self.config = config
        self.shutdown_event = shutdown_event
        self.shared_state = SharedState()
        self.autograsper = grasper
        # Message queue for non-UI messages.
        self.msg_queue = Queue()
        # Separate UI queue so that image updates can be handled in the main thread.
        self.ui_queue = Queue()

        # Read configuration with explicit error handling.
        try:
            experiment_config = config["experiment"]
            camera_config = config["camera"]
            self.experiment_name = experiment_config["name"]
            self.timeout_between_experiments = experiment_config[
                "timeout_between_experiments"
            ]
            self.save_data = camera_config["record"]
        except KeyError as e:
            raise ValueError(f"Missing configuration key in coordinator: {e}") from e
        except TypeError as e:
            raise ValueError(f"Invalid configuration format in coordinator: {e}") from e

    def _monitor_state(self):
        """
        Polls the autograsper and recorder for updates and posts messages to the message queue.
        """
        while not self.shutdown_event.is_set():
            # Post state update message.
            state_msg = {"type": "state_update", "state": self.autograsper.state}
            self.msg_queue.put(state_msg)

            self._check_if_record_is_requested()

            # If a recorder exists, push an image update message onto the UI queue.
            if self.shared_state.recorder is not None:
                bottom_img = self.shared_state.recorder.bottom_image
                if bottom_img is not None:
                    ui_msg = {"type": "image_update", "image": bottom_img.copy()}
                    self.ui_queue.put(ui_msg)
                    # TODO make this safe against race conditions
                    self.autograsper.bottom_image = bottom_img.copy()
                    self.autograsper.robot_state = self.shared_state.recorder.state
            self.shutdown_event.wait(timeout=0.1)

    def _check_if_record_is_requested(self):
        if (
            self.autograsper.request_state_record
            and self.shared_state.recorder is not None
        ):
            with self.shared_state.recorder.snapshot_cond:
                self.shared_state.recorder.take_snapshot += 1
                while self.shared_state.recorder.take_snapshot > 0:
                    self.shared_state.recorder.snapshot_cond.wait(timeout=1.0)
            self.autograsper.request_state_record = False
            self.autograsper.state_recorded_event.set()

    def _process_messages(self):
        """
        Processes non-UI messages from the message queue.
        """
        prev_state = RobotActivity.STARTUP
        self.session_dir, self.task_dir, self.restore_dir = "", "", ""
        while not self.shutdown_event.is_set():
            try:
                msg = self.msg_queue.get(timeout=0.2)
            except Empty:
                continue

            if msg["type"] == "state_update":
                current_state = msg["state"]
                if current_state != prev_state:
                    self._on_state_transition(prev_state, current_state)
                    if current_state == RobotActivity.ACTIVE:
                        if self.save_data:
                            self._create_new_data_point()
                        self._on_active_state()
                    elif current_state == RobotActivity.RESETTING:
                        self._on_resetting_state()
                    elif current_state == RobotActivity.FINISHED:
                        self._on_finished_state()
                        break
                    prev_state = current_state
            self.msg_queue.task_done()

    def _on_state_transition(self, old_state, new_state):
        if new_state == RobotActivity.STARTUP and old_state != RobotActivity.STARTUP:
            if self.shared_state.recorder:
                self.shared_state.recorder.pause = True
                time.sleep(self.timeout_between_experiments)
                self.shared_state.recorder.pause = False

    def _create_new_data_point(self):
        base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "recorded_data",
            self.experiment_name,
        )
        self.session_dir, self.task_dir, self.restore_dir = (
            FileManager.get_session_dirs(base_dir)
        )

    def _on_active_state(self):
        if self.save_data:
            self.autograsper.output_dir = self.task_dir
        self._ensure_recorder_running(self.task_dir)
        # Allow some time for initialization.
        time.sleep(0.5)
        self.autograsper.start_event.set()

    def _ensure_recorder_running(self, output_dir: str):
        if not self.shared_state.recorder:
            self.shared_state.recorder = self._setup_recorder(output_dir)
            # Start the recorder in its own thread.
            self.executor.submit(self.shared_state.recorder.record)
        if self.save_data:
            self.shared_state.recorder.start_new_recording(output_dir)

    def _setup_recorder(self, output_dir: str):
        return Recorder(
            self.config, output_dir=output_dir, shutdown_event=self.shutdown_event
        )

    def _on_resetting_state(self):
        status = "fail" if self.autograsper.failed else "success"
        logger.info(f"Task result: {status}")
        if self.save_data:
            status_file = os.path.join(self.session_dir, "status.txt")
            with open(status_file, "w") as f:
                f.write(status)
            self.autograsper.output_dir = self.restore_dir
            if self.shared_state.recorder:
                self.shared_state.recorder.start_new_recording(self.restore_dir)

    def _on_finished_state(self):
        if self.shared_state.recorder:
            self.shared_state.recorder.stop()
            time.sleep(1)  # Allow recorder to finish up

    # --- Public API for running coordinator tasks ---
    def start(self):
        """
        Starts the coordinator's background tasks.
        """
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="Coord"
        )
        self.futures = [
            self.executor.submit(self.autograsper.run_grasping),
            self.executor.submit(self._monitor_state),
            self.executor.submit(self._process_messages),
        ]

    def join(self):
        """
        Blocks until the coordinator's background tasks have finished.
        """
        try:
            concurrent.futures.wait(
                self.futures, return_when=concurrent.futures.FIRST_EXCEPTION
            )
        except Exception as e:
            logger.error("Exception in coordinator tasks: %s", e)
            self.shutdown_event.set()
        finally:
            self.shutdown_event.set()
            self.executor.shutdown(wait=True)

    def get_ui_update(self, timeout: float = 0.1):
        """
        Retrieves an image update from the UI queue.
        Returns the message dict if available, or None.
        """
        try:
            return self.ui_queue.get(timeout=timeout)
        except Empty:
            return None
