import sys
import threading
import time
import cv2
import logging
import os
from flask import Flask, Response, render_template_string, request, jsonify
from coordinator import DataCollectionCoordinator
from custom_graspers.manual_grasper import WebManualGrasper
from utils import load_config


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# Create the Flask application
app = Flask(__name__)

# Global reference to the coordinator and grasper
global_coordinator = None
global_grasper = None

# HTML template with control interface
CONTROL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Robot Manual Control</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            background-color: #f0f0f0;
            margin: 0;
            padding: 10px;
        }
        #main-container {
            display: flex;
            gap: 20px;
            max-width: 1200px;
            width: 100%;
        }
        #video-container {
            border: 2px solid #333;
            border-radius: 10px;
            overflow: hidden;
            flex-shrink: 0;
        }
        #controls {
            display: grid;
            gap: 10px;
            flex-grow: 1;
            min-width: 400px;
        }
        .control-group {
            background: white;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .control-group h3 {
            margin: 0 0 8px 0;
            color: #333;
            font-size: 14px;
        }
        .button-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 5px;
            max-width: 200px;
            margin: 0 auto;
        }
        button {
            padding: 8px;
            font-size: 12px;
            border: none;
            border-radius: 4px;
            background-color: #4CAF50;
            color: white;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        button:hover {
            background-color: #45a049;
        }
        button:active {
            background-color: #3d8b40;
        }
        button.danger {
            background-color: #f44336;
        }
        button.danger:hover {
            background-color: #da190b;
        }
        .center-button {
            grid-column: 2;
        }
        .status-bar {
            display: flex;
            gap: 15px;
            padding: 8px;
            background-color: #333;
            color: white;
            border-radius: 5px;
            font-size: 12px;
            margin-bottom: 10px;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .status-label {
            color: #aaa;
        }
        .status-value {
            color: #4CAF50;
            font-weight: bold;
            min-width: 45px;
        }
        #step-size {
            width: 100%;
            margin: 5px 0;
        }
        .keyboard-hint {
            font-size: 10px;
            color: #888;
            text-align: center;
            margin-top: 3px;
        }
        .position-inputs {
            display: flex;
            gap: 8px;
            margin: 5px 0;
            align-items: center;
        }
        .position-inputs input {
            width: 60px;
            padding: 4px;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-size: 12px;
        }
        .position-inputs button {
            padding: 4px 12px;
            font-size: 11px;
        }
        .input-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        .input-label {
            font-size: 11px;
            color: #666;
        }
        h1 {
            font-size: 20px;
            margin: 10px 0;
        }
        .compact-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 5px;
        }
    </style>
</head>
<body>
    <h1>Robot Manual Control Interface</h1>
    
    <div class="status-bar">
        <div class="status-item">
            <span class="status-label">X:</span>
            <span class="status-value" id="current-x">0.000</span>
        </div>
        <div class="status-item">
            <span class="status-label">Y:</span>
            <span class="status-value" id="current-y">0.000</span>
        </div>
        <div class="status-item">
            <span class="status-label">Z:</span>
            <span class="status-value" id="current-z">0.000</span>
        </div>
        <div class="status-item">
            <span class="status-label">Rotation:</span>
            <span class="status-value" id="current-rotation">0°</span>
        </div>
        <div class="status-item">
            <span class="status-label">Gripper:</span>
            <span class="status-value" id="current-gripper">0.000</span>
        </div>
        <div class="status-item" style="margin-left: auto;">
            <span class="status-label">Status:</span>
            <span class="status-value" id="status" style="color: #4CAF50;">Ready</span>
        </div>
    </div>
    
    <div id="main-container">
        <div id="video-container">
            <img src="/video_feed" width="640" height="480">
        </div>
        
        <div id="controls">
            <div class="control-group">
                <h3>Step Size</h3>
                <input type="range" id="step-size" min="0.01" max="0.5" step="0.01" value="0.1">
                <div style="font-size: 11px;">Current: <span id="step-value">0.1</span></div>
            </div>
            
            <div class="control-group">
                <h3>Direct Position Control</h3>
                <div class="input-group">
                    <div class="position-inputs">
                        <span class="input-label">XY:</span>
                        <input type="number" id="target-x" placeholder="X" min="0" max="1" step="0.01">
                        <input type="number" id="target-y" placeholder="Y" min="0" max="1" step="0.01">
                        <button onclick="setXY()">Set XY</button>
                    </div>
                    <div class="position-inputs">
                        <span class="input-label">Z:</span>
                        <input type="number" id="target-z" placeholder="Z" min="0" max="1" step="0.01">
                        <button onclick="setZ()">Set Z</button>
                    </div>
                </div>
            </div>
            
            <div class="control-group">
                <h3>XY Movement</h3>
                <div class="button-grid">
                    <div></div>
                    <button onclick="sendCommand('move_forward')">↑</button>
                    <div></div>
                    <button onclick="sendCommand('move_left')">←</button>
                    <div></div>
                    <button onclick="sendCommand('move_right')">→</button>
                    <div></div>
                    <button onclick="sendCommand('move_backward')">↓</button>
                    <div></div>
                </div>
                <div class="keyboard-hint">Keys: W/A/S/D</div>
            </div>
            
            <div class="control-group">
                <h3>Z / Rotation / Gripper</h3>
                <div class="compact-grid">
                    <button onclick="sendCommand('move_up')">Z ↑</button>
                    <button onclick="sendCommand('move_down')">Z ↓</button>
                    <button onclick="sendCommand('rotate_left')">↺ Rot</button>
                    <button onclick="sendCommand('rotate_right')">↻ Rot</button>
                    <button onclick="sendCommand('gripper_open')">Open</button>
                    <button onclick="sendCommand('gripper_close')">Close</button>
                    <button onclick="sendCommand('gripper_open_small')" style="font-size: 10px;">Open Fine</button>
                    <button onclick="sendCommand('gripper_close_small')" style="font-size: 10px;">Close Fine</button>
                </div>
                <div class="keyboard-hint">Keys: R/F (Z), Z/X (Rot), I/O/K/L (Grip)</div>
            </div>
            
            <div class="control-group">
                <button onclick="sendCommand('stop')" class="danger" style="width: 100%;">STOP (Q)</button>
            </div>
        </div>
    </div>
    
    <script>
        // Update step size display
        const stepSlider = document.getElementById('step-size');
        const stepValue = document.getElementById('step-value');
        stepSlider.addEventListener('input', function() {
            stepValue.textContent = this.value;
        });
        
        // Update current position display
        function updatePositions() {
            fetch('/state')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('current-x').textContent = data.x.toFixed(3);
                    document.getElementById('current-y').textContent = data.y.toFixed(3);
                    document.getElementById('current-z').textContent = data.z.toFixed(3);
                    document.getElementById('current-rotation').textContent = data.rotation + '°';
                    document.getElementById('current-gripper').textContent = data.gripper.toFixed(3);
                })
                .catch((error) => {
                    console.error('Error fetching state:', error);
                });
        }
        
        // Update positions every 500ms
        setInterval(updatePositions, 500);
        
        // Set XY position directly
        function setXY() {
            const x = parseFloat(document.getElementById('target-x').value);
            const y = parseFloat(document.getElementById('target-y').value);
            
            if (isNaN(x) || isNaN(y)) {
                document.getElementById('status').textContent = 'Invalid XY values';
                document.getElementById('status').style.color = '#f44336';
                return;
            }
            
            fetch('/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    command: 'set_xy',
                    value: [x, y]
                }),
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('status').textContent = data.status;
                document.getElementById('status').style.color = '#4CAF50';
                setTimeout(() => {
                    document.getElementById('status').textContent = 'Ready';
                }, 1000);
            });
        }
        
        // Set Z position directly
        function setZ() {
            const z = parseFloat(document.getElementById('target-z').value);
            
            if (isNaN(z)) {
                document.getElementById('status').textContent = 'Invalid Z value';
                document.getElementById('status').style.color = '#f44336';
                return;
            }
            
            fetch('/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    command: 'set_z',
                    value: z
                }),
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('status').textContent = data.status;
                document.getElementById('status').style.color = '#4CAF50';
                setTimeout(() => {
                    document.getElementById('status').textContent = 'Ready';
                }, 1000);
            });
        }
        
        // Send command to server
        function sendCommand(command) {
            const stepSize = parseFloat(stepSlider.value);
            fetch('/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    command: command,
                    step_size: stepSize
                }),
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('status').textContent = data.status;
                document.getElementById('status').style.color = '#4CAF50';
                setTimeout(() => {
                    document.getElementById('status').textContent = 'Ready';
                }, 1000);
            })
            .catch((error) => {
                console.error('Error:', error);
                document.getElementById('status').textContent = 'Error';
                document.getElementById('status').style.color = '#f44336';
            });
        }
        
        // Keyboard controls
        document.addEventListener('keydown', function(event) {
            // Don't trigger if typing in input fields
            if (event.target.tagName === 'INPUT') return;
            
            const key = event.key.toLowerCase();
            const keyMap = {
                'w': 'move_forward',
                'a': 'move_left',
                's': 'move_backward',
                'd': 'move_right',
                'r': 'move_up',
                'f': 'move_down',
                'i': 'gripper_open',
                'o': 'gripper_open_small',
                'k': 'gripper_close',
                'l': 'gripper_close_small',
                'z': 'rotate_left',
                'x': 'rotate_right',
                'q': 'stop'
            };
            
            if (keyMap[key]) {
                event.preventDefault();
                sendCommand(keyMap[key]);
            }
        });
        
        // Initial position update
        updatePositions();
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Main page with control interface."""
    return render_template_string(CONTROL_TEMPLATE)


@app.route("/video_feed")
def video_feed():
    """Route that streams the video feed as an MJPEG stream."""
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/state", methods=["GET"])
def get_state():
    """Get current robot state."""
    global global_grasper

    if not global_grasper:
        return jsonify({"error": "Grasper not initialized"}), 500

    try:
        state = global_grasper.get_current_state()
        return jsonify(state)
    except Exception as e:
        logging.error(f"Error getting state: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/control", methods=["POST"])
def control():
    """Handle control commands from the web interface."""
    global global_grasper

    if not global_grasper:
        return jsonify({"status": "Grasper not initialized", "success": False}), 500

    try:
        data = request.json
        command = data.get("command")

        # Handle different value types
        if command in ["set_xy", "set_z"]:
            value = data.get("value")
        else:
            value = data.get("step_size", 0.1)

        # Send command to the grasper
        success = global_grasper.send_command(command, value)

        if success:
            return jsonify({"status": f"Command '{command}' sent", "success": True})
        else:
            return jsonify({"status": "Control not active", "success": False})

    except Exception as e:
        logging.error(f"Error processing control command: {e}")
        return jsonify({"status": str(e), "success": False}), 500


def generate_frames():
    """
    Generator function that continuously retrieves image frames from the
    coordinator's UI update queue, encodes them as JPEG, and yields them.
    """
    while not global_coordinator.shutdown_event.is_set():
        ui_msg = global_coordinator.get_ui_update(timeout=0.1)
        if ui_msg and ui_msg.get("type") == "image_update":
            frame = ui_msg.get("image")
            if frame is not None:
                # Encode frame as JPEG
                ret, jpeg = cv2.imencode(".jpg", frame)
                if ret:
                    frame_bytes = jpeg.tobytes()
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n\r\n"
                    )
        else:
            # If no frame is available, sleep briefly
            time.sleep(0.02)


def main():
    global global_coordinator, global_grasper

    config_path = os.path.join(os.getcwd(), "autograsper", "my_config.yaml")
    config = load_config(config_path)
    shutdown_event = threading.Event()

    # Create the web-controlled grasper
    global_grasper = WebManualGrasper(config, shutdown_event=shutdown_event)
    global_coordinator = DataCollectionCoordinator(
        config, global_grasper, shutdown_event
    )

    # Start the coordinator
    global_coordinator.start()

    try:
        # Run Flask app
        app.run(host="0.0.0.0", port=3001, debug=False, threaded=True)
    except Exception as e:
        logging.error("Flask app error: %s", e)
    finally:
        shutdown_event.set()
        global_coordinator.join()
        logging.info("Application shutdown complete.")
        sys.exit(0)


if __name__ == "__main__":
    main()
