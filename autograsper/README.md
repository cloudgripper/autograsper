# Autograsper

Autograsper is a toolkit and framework for controlling, observing, and setting up autonomous data collection with the **CloudGripper** robot. It provides a modular platform to easily create custom robot behaviors (or “graspers”), record sensor and state data, and manage data collection sessions—all in a few lines of code.


## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Creating a Custom Grasper](#creating-a-custom-grasper)
    - [Example: `ExampleGrasper`](#example-examplegrasper)
- [Troubleshooting & FAQs](#troubleshooting--faqs)
- [Contributing](#contributing)
- [License](#license)

## Installation

1. **Clone the Repository:**

```bash
git clone https://github.com/axel-kaliff/cloudgripper-api
cd cloudgripper-api
```

2. **Set up a Virtual Environment & Install Dependencies**
This can be done with devcontainers, conda, or venv.

Example using venv:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```


3. **Configure Environment Variables:**

The project requires a CloudGripper API token. Set the environment variable `CLOUDGRIPPER_TOKEN`:
```bash
export CLOUDGRIPPER_TOKEN="your_cloudgripper_token_here"  # Linux/MacOS
set CLOUDGRIPPER_TOKEN=your_cloudgripper_token_here          # Windows
```

or use a `.env` file in the root of your project:

```
CLOUDGRIPPER_TOKEN="your_cloudgripper_token_here"
```

## Quick Start

Autograsper can be started with the main controller script. By default, it uses the configuration file at `autograsper/config.ini`.

```bash
cd autograsper
python main.py
```

This command starts the **Data Collection Coordinator**, which manages both robot control and data recording.

## Configuration

The `config.ini` file is used to set up experiment and camera parameters. You can find an example configuration at `autograsper/config.ini`. Configurations include, but are not limited to:
- Toggling saving data to file or just observing the CloudGripper without recording data
- Recording frequency (FPS)
- Toggling continously capturing data or only after an action has been performed 
- Toggling storing camera frames as individual pictures or compile into `mp4`
- Changing default time delay between robot actions

## Creating a Custom Grasper

Autograsper’s core functionality is built around the abstract class `AutograsperBase` (found in `grasper.py`). To create your own grasper:

1. **Create a New Python File:**  
    For example, `custom_graspers/my_custom_grasper.py`.
2. **Import and Extend `AutograsperBase`:**
```python
from grasper import AutograsperBase
from library.utils import OrderType
import time

class MyCustomGrasper(AutograsperBase):
    def __init__(self, config):
        super().__init__(config)

    def perform_task(self):
        # Use queue_orders() to execute a sequence of actions
        self.queue_orders(
            [
                (OrderType.MOVE_XY, [0.5, 0.5]),
                (OrderType.ROTATE, [45]),
                (OrderType.MOVE_Z, [0.8]),
                (OrderType.GRIPPER_OPEN, []),
            ],
            time_between_orders=self.time_between_orders # set in config.ini file
        )
```

3. **Integrate Your Custom Grasper:**
In `main.py`, import your grasper and replace the example class to instantiate your custom grasper instead. For example:

```python
# Replace the default import with your custom grasper
from custom_graspers.my_custom_grasper import MyCustomGrasper

config_file = "autograsper/config.ini"
grasper = MyCustomGrasper(config_file)
```

### Example: `ExampleGrasper`

An example grasper is provided to illustrate two ways of controlling the robot:

1. **Batch Commanding with `queue_orders()`:**  
    Queue several commands to be executed sequentially. If `record_only_after_action` is set to True in `config.ini`, the `record_current_state()` will automatically be called after every action and its time delay.
    
2. **Direct Commanding:**  
    Execute commands one-by-one with delays and record the state after each command.

```python
from grasper import AutograsperBase, RobotActivity
from library.utils import OrderType
import time


class ExampleGrasper(AutograsperBase):
    def __init__(self, config):
        super().__init__(config)

    def perform_task(self):
        # Method 1: Using queue_orders to send a batch of commands
        self.queue_orders(
            [
                (OrderType.MOVE_XY, [0.5, 0.5]),
                (OrderType.ROTATE, [30]),
                (OrderType.MOVE_Z, [0.7]),
                (OrderType.GRIPPER_OPEN, []),
            ],
            time_between_orders=self.time_between_orders  # set in config.ini file
        )

        # Method 2: Sending individual commands with state recording
        self.robot.move_xy(0.5, 0.5)
        time.sleep(2)
        self.record_current_state()

        self.robot.rotate(30)
        time.sleep(2)
        self.record_current_state()

        self.robot.move_z(0.7)
        time.sleep(2)
        self.record_current_state()

        self.robot.gripper_open()
        time.sleep(2)
        self.record_current_state()

        # comment or remove if you want multiple experiments to run
        self.state = RobotActivity.FINISHED  # stop data recording

```

### Adding startup and reset functions

To perform actions at the start or end of an experiment, you can define the `startup` and `reset_task` functions.

```python
    def startup(self):
        # This method will execute at the beginning of every experiment.
        # During this phase, data will not be recorded.

        print("performing startup tasks...")

        self.queue_orders(
            [
                (OrderType.MOVE_XY, [0.1, 0.1]),
                (OrderType.ROTATE, [0]),
                (OrderType.MOVE_Z, [1]),
                (OrderType.GRIPPER_CLOSE, []),
            ],
            time_between_orders=self.time_between_orders  # set in config.ini file
        )

    def reset_task(self):
        # replace with your own resetting if needed
        return super().reset_task()
```

Use this example as a starting point for designing more complex tasks and integrating additional sensor data or feedback loops.

### Example: `Manual Control`
To control the gripper manually you can use the `manual_control` function.

```python
from grasper import AutograsperBase, RobotActivity

class ManualGrasper(AutograsperBase):
    def __init__(self, config):
        super().__init__(config)

    def perform_task(self):

        self.manual_control()

        self.state = RobotActivity.FINISHED  # stop data recording

    def reset_task(self):
        # replace with your own resetting if needed
        return super().reset_task()

```

### Advanced Examples
More advanced examples can be found in the `custom_graspers` directory. This includes evaluating task success, integrating resetting functions etc. Basic examples of resetting and task evaluation will be posted on this README soon.

## Troubleshooting & FAQs

**Q: The robot does not start recording.**  
**A:** Verify that the `CLOUDGRIPPER_TOKEN` environment variable is set correctly and that your `config.ini` file has recording enabled.

**Q: I encounter errors when parsing the configuration file.**  
**A:** Double-check your `config.ini` syntax. Use Python literal notation for lists and dictionaries, and ensure all required parameters are provided.

**Q: Video files are missing or incomplete.**  
**A:** Ensure that the output directories have proper write permissions and that the camera calibration parameters in your configuration are correct.

**Q: Recorded images capture the robot mid-action, not after the action is complete.**  
**A:** When recording is set to only record frames after actions, images are requested after an action is performed *and* the action time delay. If performing manual capture requests (method 2 above), add some time after the action and the request. If using `queue_orders` (method 1), either set a higher time delay value in the function call or change the default in your `config.ini` file.


_For more detailed troubleshooting, please refer to the [Issues](https://github.com/axel-kaliff/cloudgripper-api/issues) section on GitHub._

## Contributing

Contributions are welcome! If you’d like to improve Autograsper or add new features:

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Open a pull request.

_For major changes, please open an issue first to discuss what you would like to change._
