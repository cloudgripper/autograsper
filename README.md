# Project Documentation

## Introduction

This project contains the Autograsper toolkit and involves automation of robotic stacking tasks using a CloudGripper robot. Includes robot control and data collection. Currently containing stacking task example but can generalize to many manipulation tasks.

### Example Dataset
An **example dataset** collected using Autograsper containing over 200 episodes of stacking and destacking can be found [here](https://cloudgripper.eecs.kth.se:8443/dataset/download/Autograsper_sample_dataset.zip).

### Compatability with CloudGripper Simulation
This toolkit is compatible with the CloudGripper MuJoCo simulation, which will be published soon. The mirroring functionality of the real CloudGripper API and the simulation API enables switching between the two environments by changing only **one line of code**. Below is an illustration of the same Autograsper script being run on the respective environments.

![compare](https://github.com/user-attachments/assets/fb710cf8-9b92-4c1c-8df6-44a5c08db3fe)


### **Featuring:**

- **utils**: a set of general functions intended for any project.
- **autograsper**: an example of scheduling a loop of stacking tasks, can be used as template for robot control.
- **recorder**: a class that records all robot data during tasks and stores it in a clear and structured way.
- **thread_manager**: an example of using all above to perform and record a large number of robot tasks.

# Usage Guide

## Setting Up Your Environment

### Step 1: Install Dependencies

#### 1.A: Setup virtual environment and install dependencies
Ensure you have Python 3.x installed. 
Create a virtual environment
```sh
python -m venv venv
```
Install the required dependencies:
```sh
pip install -r requirements.txt
```

#### 1.B: CloudGripper API
Clone the [CloudGripper API repo](https://github.com/cloudgripper/cloudgripper-api), place the Autograsper code in that directory. Move the `utils.py` and `rgb_object_tracker.py` file to the `library` directory.

### Step 2: Set Environment Variables

The code requires an environment variable `ROBOT_TOKEN` to authenticate with the GripperRobot API. Create a `.env` file in the project root with the following content:

```env
ROBOT_TOKEN=your_robot_token_here
```

## Running the Code

### Running the Autograsper

The `autograsper.py` script is controls the robot to perform stacking tasks. Can be used as a template for scheduled robot control.

1. **Command-Line Arguments**:

   - `--robot_idx`: The index of the robot to be controlled.
   - `--output_dir`: The directory to save state data.

2. **Example Command**:

   ```sh
   python Autograsper/autograsper.py --robot_idx 1 --output_dir /path/to/output
   ```

3. **Description**:
   - Initializes the `Autograsper` class.
   - Runs the main grasping loop, where the robot performs a series of tasks such as moving, gripping, and placing objects.
   - Saves the state of the robot after each action for later analysis.

### Recording the Robot's Actions

The `recorder.py` script records the robot's actions, capturing both top and bottom camera views.

1. **Command-Line Arguments**:

   - `--robot_idx`: The index of the robot to be recorded.
   - `--output_dir`: The directory to save recorded videos and final images.

2. **Example Command**:

   ```sh
   python Autograsper/recorder.py --robot_idx 1 --output_dir /path/to/output
   ```

3. **Description**:
   - Initializes the `Recorder` class.
   - Records the robot's actions, saving video files at specified intervals.
   - Displays the bottom camera view and waits for user input to stop recording.

# How to Define a Task

This framework provides an extensible base class for defining custom robot tasks. Here's how you can define a new task using the existing toolkit:

## Step 1: Create a New Task Class

To define a new task, create a new Python class that inherits from `AutograsperBase`. This abstract base class provides common functionality for initializing the robot, camera calibration, and controlling the robot. You must implement specific task behaviors by overriding two key methods: `perform_task()` and `reset_task()`.

```python
from grasper import AutograsperBase
from library.rgb_object_tracker import get_object_pos
from library.utils import OrderType

class NewTaskAutograsper(AutograsperBase):
    def __init__(
        self,
        args,
        output_dir: str = "",
        camera_matrix=None,
        distortion_coefficients=None,
    ):
        super().__init__(args, output_dir, camera_matrix, distortion_coefficients)
        # Custom task-specific initialization goes here

    def perform_task(self):
        # Implement the specific logic for this task here
        object_position = get_object_pos(self.bottom_image, self.robot_idx, "target_color")
        self.pickup_and_place_object(
            object_position,
            object_height=0,
            target_height=0,
            target_position=[0.5, 0.5],
        )

    def reset_task(self):
        # Reset the environment after performing the task
        print("Resetting task to original state")
```

## Step 2: Override Task-Specific Methods

### `perform_task()`
This method should contain the core logic of the task. Use methods like `pickup_and_place_object()` to implement the series of actions the robot should perform. For example, the robot may be instructed to move to an object, pick it up, and place it at a target location.

### `reset_task()`
After the task is complete, the `reset_task()` method should bring the environment back to the starting state. This could include resetting the position of objects or performing cleanup actions to ensure the next task can start correctly.

## Step 3: Use Helper Methods

The base class provides several utility methods you can use to simplify your task implementation:

- **`queue_robot_orders()`**: Queue up a list of commands for the robot.
- **`pickup_and_place_object()`**: Pick up an object from one position and move it to another.
- **`wait_for_start_signal()`**: Wait for a signal to start the task, useful for coordinating tasks.

These helper methods make it easier to manage common operations like moving the robot arm, picking objects, or executing a sequence of commands.

## Example Task

Below is a simple example that defines a new task in which the robot picks up a blue block and places it at a specific location:

```python
class BlueBlockPicker(AutograsperBase):
    def perform_task(self):
        blue_block_position = get_object_pos(self.bottom_image, self.robot_idx, "blue")
        self.pickup_and_place_object(
            blue_block_position,
            object_height=0.05,
            target_height=0.1,
            target_position=[0.7, 0.7],
        )

    def reset_task(self):
        # Bring the blue block back to the starting area
        self.recover_after_fail()
```


# Modules Overview

### utils.py

The utils module provides a set of standard functions intented to be useful with any project

#### Enums

- `OrderType`: Enum to define different types of robot orders (MOVE_XY, MOVE_Z, GRIPPER_CLOSE, GRIPPER_OPEN).

#### Functions

- `save_state(robot, output_dir, start_time, previous_order)`: Saves the current state of the robot.
- `execute_order(robot, order, output_dir, start_time, reverse_xy)`: Executes a single order on the robot.
- `queue_orders(robot, order_list, time_between_orders, output_dir, start_time, reverse_xy)`: Queues and executes a list of orders sequentially.
- `queue_orders_with_input(robot, order_list, output_dir, start_time)`: Queues and executes orders with user input between commands.
- `snowflake_sweep(robot)`: Performs a snowflake sweep pattern with the robot.
- `sweep_straight(robot)`: Performs a straight sweep pattern with the robot.
- `recover_gripper(robot)`: Recovers the gripper by fully opening and then closing it.
- `generate_position_grid()`: Generates a grid of positions.
- `pick_random_positions(position_bank, n_layers, object_size, avoid_positions)`: Picks random positions from a grid.
- `get_undistorted_bottom_image(robot, m, d)`: Gets an undistorted image from the robot's camera.

### autograsper.py

The autograsper module is an example usage of the utils functions that scripts tasks for the CloudGripper robot.

#### Classes

- `RobotActivity`: Enum to define different states of the robot (ACTIVE, RESETTING, FINISHED, STARTUP).
- `Autograsper`: Main class to handle the autograsping process.

#### Methods

- `__init__(self, args, output_dir)`: Initializes the Autograsper.
- `pickup_and_place_object(self, object_position, object_height, target_height, target_position, time_between_orders)`: Picks up and places an object.
- `reset(self, block_positions, block_heights, stack_position, time_between_orders)`: Resets the blocks to their initial positions.
- `clear_center(self)`: Clears the center area of the workspace.
- `startup(self, position)`: Performs a startup sequence at a given position.
- `run_grasping(self)`: Runs the main grasping loop.

#### Main Execution

- Sets up command-line argument parsing and initializes the `Autograsper` instance to start the grasping process.

### recording.py

#### Classes

- `Recorder`: Main class to handle the recording of the robot's actions.

#### Methods

- `__init__(self, session_id, output_dir, m, d, token, idx)`: Initializes the Recorder.
- `_start_new_video(self, output_video_dir, output_bottom_video_dir, video_counter, fourcc, image_shape, bottom_image_shape)`: Starts a new video recording session.
- `record(self, start_new_video_every)`: Records the robot's actions.
- `_initialize_directories(self)`: Initializes the directories for saving recordings.
- `start_new_recording(self, new_output_dir)`: Starts a new recording in a different directory.
- `stop(self)`: Stops the recording process.

#### Main Execution

- Sets up command-line argument parsing and initializes the `Recorder` instance to start recording.

### thread_manager.py

#### Functions

- `get_new_session_id(base_dir)`: Generates a new session ID based on existing directories.
- `run_autograsper(autograsper)`: Runs the autograsper process.
- `setup_recorder(output_dir, robot_idx)`: Sets up the recorder with given parameters.
- `run_recorder(recorder)`: Runs the recorder process.
- `state_monitor(autograsper)`: Monitors the state of the autograsper.

#### Main Execution

- Sets up command-line argument parsing and initializes the `Autograsper` and `Recorder` instances to run in parallel. It monitors their states and manages session directories.
