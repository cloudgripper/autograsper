# grasper.py
from abc import ABC, abstractmethod
import os
import sys
import time
from enum import Enum
from typing import List, Tuple
import threading
from dotenv import load_dotenv

# Ensure project root is in the system path.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from client.cloudgripper_client import GripperRobot
import library.utils as utils

load_dotenv()


class RobotActivity(Enum):
    ACTIVE = 1
    RESETTING = 2
    FINISHED = 3
    STARTUP = 4


def sleep_with_shutdown(duration: float, shutdown_event: threading.Event):
    """Sleep in small increments, checking for shutdown."""
    end_time = time.time() + duration
    while time.time() < end_time:
        if shutdown_event.is_set():
            break
        time.sleep(0.05)


class AutograsperBase(ABC):
    def __init__(
        self, config, output_dir: str = "", shutdown_event: threading.Event = None
    ):
        if shutdown_event is None:
            raise ValueError("shutdown_event must be provided")
        self.shutdown_event = shutdown_event

        self.bottom_image = None

        self.token = os.getenv("CLOUDGRIPPER_TOKEN")
        if not self.token:
            raise ValueError("CLOUDGRIPPER_TOKEN environment variable not set")

        self.output_dir = output_dir
        self.start_time = time.time()
        self.failed = False

        self.state = RobotActivity.STARTUP
        self.start_event = threading.Event()
        self.state_recorded_event = threading.Event()

        self.request_state_record = False
        self.task_time_margin = 2
        self.robot_state = None

        try:
            camera_config = config["camera"]
            experiment_config = config["experiment"]
            self.record_only_after_action = bool(
                camera_config["record_only_after_action"]
            )
            self.robot_idx = experiment_config["robot_idx"]
            self.time_between_orders = experiment_config["time_between_orders"]
        except KeyError as e:
            raise ValueError(
                f"Missing configuration key in AutograsperBase: {e}"
            ) from e
        except TypeError as e:
            raise ValueError(
                f"Invalid configuration format in AutograsperBase: {e}"
            ) from e

        self.robot = self.initialize_robot()

    def initialize_robot(self) -> GripperRobot:
        try:
            return GripperRobot(self.robot_idx, self.token)
        except Exception as e:
            raise ValueError("Invalid robot ID or token: ", e) from e

    def record_current_state(self):
        """Request a state record and wait until processed or shutdown."""
        self.request_state_record = True
        self.state_recorded_event.clear()
        while not self.shutdown_event.is_set():
            if self.state_recorded_event.wait(timeout=0.1):
                return

    def wait_for_start_signal(self):
        """Wait for the start event, checking periodically for shutdown."""
        while not self.shutdown_event.is_set():
            if self.start_event.wait(timeout=0.05):
                self.start_event.clear()  # Clear for next cycle.
                return

    def run_grasping(self):
        """
        A simple state-machine loop:
          - STARTUP: Run startup logic, then move to ACTIVE.
          - ACTIVE: Wait for start signal, perform task.
          - RESETTING: After task, sleep and either recover (if failed) or reset.
        """
        while self.state != RobotActivity.FINISHED and not self.shutdown_event.is_set():
            if self.state == RobotActivity.STARTUP:
                self.startup()
                self.state = RobotActivity.ACTIVE
            elif self.state == RobotActivity.ACTIVE:
                self.wait_for_start_signal()
                try:
                    self.perform_task()
                except Exception as e:
                    print(f"Unexpected error during perform_task: {e}")
                    self.failed = True
                    raise Exception(e)
                    self.shutdown_event.set()
                if self.shutdown_event.is_set() or self.state == RobotActivity.FINISHED:
                    break
                self.state = RobotActivity.RESETTING
            elif self.state == RobotActivity.RESETTING:
                sleep_with_shutdown(self.task_time_margin, self.shutdown_event)
                if self.failed:
                    print("Experiment failed, recovering")
                    self.recover_after_fail()
                    self.failed = False
                else:
                    self.reset_task()
                self.state = RobotActivity.STARTUP
            else:
                break

    def recover_after_fail(self):
        """Override to implement recovery logic after failure."""
        pass

    @abstractmethod
    def perform_task(self):
        """
        Override to perform robot actions.
        Default implementation prints a message periodically.
        """
        while not self.shutdown_event.is_set():
            print(
                "GRASPER: No task defined. Override perform_task() to perform robot actions."
            )
            sleep_with_shutdown(0.5, self.shutdown_event)
        print("GRASPER: Exiting perform_task() due to shutdown signal.")

    def reset_task(self):
        """Override to implement logic for resetting between tasks."""
        pass

    def startup(self):
        """Override to implement initialization logic before a task."""
        pass

    def get_state(self):
        "Update state for robot"

        self.robot_state = self.robot.get_state()

        return self.robot_state

    def execute_order(self, order, output_dir, reverse_xy):
        utils.execute_order(self.robot, order, output_dir, reverse_xy)

    def queue_orders(
        self,
        order_list: List[Tuple],
        time_between_orders: float = None,
        output_dir: str = "",
        reverse_xy: bool = False,
        record=True,
    ):
        """
        Queue a list of orders for the robot to execute sequentially and save state after each order.
        """
        if time_between_orders is None:
            time_between_orders = self.time_between_orders

        for order in order_list:
            if self.shutdown_event.is_set():
                break
            self.execute_order(order, output_dir, reverse_xy)
            sleep_with_shutdown(time_between_orders, self.shutdown_event)
            if (
                record
                and self.record_only_after_action
                and (self.state in (RobotActivity.ACTIVE, RobotActivity.RESETTING))
            ):
                self.record_current_state()
