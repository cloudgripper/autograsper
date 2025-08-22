from grasper import AutograsperBase, RobotActivity
from library.utils import OrderType
import numpy as np
import queue
import time


class WebManualGrasper(AutograsperBase):
    def __init__(self, config, shutdown_event):
        super().__init__(config, shutdown_event=shutdown_event)
        # Queue for receiving commands from web interface
        self.command_queue = queue.Queue()
        self.control_active = False

    def perform_task(self):
        """Main task that processes commands from the web interface."""
        self.control_active = True
        self.web_control()
        self.state = RobotActivity.FINISHED  # stop data recording

    def reset_task(self):
        """Reset the task and clear any pending commands."""
        # Clear the command queue
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except queue.Empty:
                break
        return super().reset_task()

    def get_current_state(self):
        """
        Get the current state of the robot.
        Returns dict with current positions.
        """
        if self.robot_state is None:
            self.robot_state, _ = self.get_state()

        return {
            "x": self.robot_state.get("x_norm", 0),
            "y": self.robot_state.get("y_norm", 0),
            "z": self.robot_state.get("z_norm", 0),
            "rotation": self.robot_state.get("rotation", 0),
            "gripper": self.robot_state.get("claw_norm", 0),
        }

    def send_command(self, command_type, value=None):
        """
        Public method to be called from the Flask routes.
        Adds commands to the queue for processing.
        """
        if self.control_active:
            self.command_queue.put(
                {"type": command_type, "value": value, "timestamp": time.time()}
            )
            return True
        return False

    def web_control(self, step_size=0.1, time_between_orders=None):
        """
        Process commands from the web interface queue.
        """
        if self.robot_state is None:
            self.robot_state, _ = self.get_state()
        if time_between_orders is None:
            time_between_orders = self.time_between_orders

        current_x = self.robot_state["x_norm"]
        current_y = self.robot_state["y_norm"]
        current_z = self.robot_state["z_norm"]
        current_rotation = self.robot_state["rotation"]
        current_angle = self.robot_state["claw_norm"]

        print("Web control active. Waiting for commands...")

        while not self.shutdown_event.is_set():
            try:
                # Wait for command with timeout
                command = self.command_queue.get(timeout=0.1)

                cmd_type = command["type"]
                cmd_value = command.get("value", step_size)

                # Process different command types
                if cmd_type == "move_forward":
                    current_y += cmd_value
                    current_y = min(max(current_y, 0), 1)
                    self.queue_orders(
                        [(OrderType.MOVE_XY, [current_x, current_y])],
                        time_between_orders,
                    )

                elif cmd_type == "move_backward":
                    current_y -= cmd_value
                    current_y = min(max(current_y, 0), 1)
                    self.queue_orders(
                        [(OrderType.MOVE_XY, [current_x, current_y])],
                        time_between_orders,
                    )

                elif cmd_type == "move_left":
                    current_x -= cmd_value
                    current_x = min(max(current_x, 0), 1)
                    self.queue_orders(
                        [(OrderType.MOVE_XY, [current_x, current_y])],
                        time_between_orders,
                    )

                elif cmd_type == "move_right":
                    current_x += cmd_value
                    current_x = min(max(current_x, 0), 1)
                    self.queue_orders(
                        [(OrderType.MOVE_XY, [current_x, current_y])],
                        time_between_orders,
                    )

                elif cmd_type == "move_up":
                    current_z += cmd_value
                    current_z = min(max(current_z, 0), 1)
                    print(f"Z position: {current_z}")
                    self.queue_orders(
                        [(OrderType.MOVE_Z, [current_z])], time_between_orders
                    )

                elif cmd_type == "move_down":
                    current_z -= cmd_value
                    current_z = min(max(current_z, 0), 1)
                    print(f"Z position: {current_z}")
                    self.queue_orders(
                        [(OrderType.MOVE_Z, [current_z])], time_between_orders
                    )

                elif cmd_type == "gripper_open":
                    current_angle += cmd_value / 100
                    current_angle = min(current_angle, 1)
                    print(f"Gripper angle: {current_angle}")
                    self.queue_orders(
                        [(OrderType.GRIPPER_CLOSE, [current_angle])],
                        time_between_orders,
                    )

                elif cmd_type == "gripper_open_small":
                    current_angle += cmd_value / 200
                    current_angle = min(current_angle, 1)
                    print(f"Gripper angle: {current_angle}")
                    self.queue_orders(
                        [(OrderType.GRIPPER_CLOSE, [current_angle])],
                        time_between_orders,
                    )

                elif cmd_type == "gripper_close":
                    current_angle -= cmd_value / 100
                    current_angle = max(current_angle, 0.2)
                    print(f"Gripper angle: {current_angle}")
                    self.queue_orders(
                        [(OrderType.GRIPPER_CLOSE, [current_angle])],
                        time_between_orders,
                    )

                elif cmd_type == "gripper_close_small":
                    current_angle -= cmd_value / 200
                    current_angle = max(current_angle, 0.2)
                    print(f"Gripper angle: {current_angle}")
                    self.queue_orders(
                        [(OrderType.GRIPPER_CLOSE, [current_angle])],
                        time_between_orders,
                    )

                elif cmd_type == "rotate_left":
                    current_rotation -= int(cmd_value * 100)
                    current_rotation = np.clip(current_rotation, 0, 360)
                    print(f"Rotation: {current_rotation}")
                    self.queue_orders(
                        [(OrderType.ROTATE, [current_rotation])], time_between_orders
                    )

                elif cmd_type == "rotate_right":
                    current_rotation += int(cmd_value * 100)
                    current_rotation = np.clip(current_rotation, 0, 360)
                    print(f"Rotation: {current_rotation}")
                    self.queue_orders(
                        [(OrderType.ROTATE, [current_rotation])], time_between_orders
                    )

                elif cmd_type == "stop":
                    print("Stop command received")
                    self.control_active = False
                    break

                elif cmd_type == "set_xy":
                    # Direct XY position setting
                    if cmd_value and len(cmd_value) == 2:
                        current_x = min(max(float(cmd_value[0]), 0), 1)
                        current_y = min(max(float(cmd_value[1]), 0), 1)
                        self.queue_orders(
                            [(OrderType.MOVE_XY, [current_x, current_y])],
                            time_between_orders,
                        )
                        print(f"Set XY to: ({current_x:.3f}, {current_y:.3f})")

                elif cmd_type == "set_z":
                    # Direct Z position setting
                    if cmd_value is not None:
                        current_z = min(max(float(cmd_value), 0), 1)
                        self.queue_orders(
                            [(OrderType.MOVE_Z, [current_z])],
                            time_between_orders,
                        )
                        print(f"Set Z to: {current_z:.3f}")

                elif cmd_type == "get_state":
                    # Return current state
                    state = {
                        "x": current_x,
                        "y": current_y,
                        "z": current_z,
                        "rotation": current_rotation,
                        "gripper": current_angle,
                    }
                    print(f"Current state: {state}")

            except queue.Empty:
                # No command available, continue
                continue
            except Exception as e:
                print(f"Error processing command: {e}")

        self.control_active = False
        print("Web control stopped")

