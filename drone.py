import asyncio
import random
import logging
import sys
import os
from tcdicn import Node

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Drone:
    def __init__(self, drone_id, port):
        logging.info(f"Initializing drone {drone_id} on port {port}")
        # Initialize the drone with a unique ID and network information
        self.node = Node()  # Node instance for network communication
        self.drone_id = drone_id
        self.port = port        # Port for this drone's node
        self.position = (0, 0)  # Initial position (x, y)
        self.temperature = 20  # Initial temperature in Celsius
        self.battery = 100  # Initial battery percentage
        self.altitude = 0  # Altitude
        self.speed = 0  # Speed of the drone
        self.camera = False  # Camera status
        self.lights = False  # Lights status
        self.communicator = False  # Status of the communicator

    async def update_sensors(self):
        # Continuously update sensor readings and publish them
        while True:
            if self.communicator:
                # Simulate sensor reading changes
                self.position = (self.position[0] + random.uniform(-0.1, 0.1),
                                 self.position[1] + random.uniform(-0.1, 0.1))
                self.temperature += random.uniform(-0.5, 0.5)
                self.battery -= 1
                self.altitude += random.uniform(-0.1, 0.1)
                self.speed += random.uniform(-0.1, 0.1)
                
                # Publish sensor readings using ICN
                await self.node.set(f"{self.drone_id}-data", str(self.get_sensor_data()))

            await asyncio.sleep(5)

    def get_sensor_data(self):
        # Return current sensor data as a dictionary
        return {
            "position": self.position,
            "temperature": self.temperature,
            "battery": self.battery,
            "altitude": self.altitude,
            "speed": self.speed,
            "camera": self.camera,
            "lights": self.lights,
            "communicator": self.communicator
        }

    async def process_command(self, command):
        # Process incoming commands
        key, value = command.split('=')
        if key == "communicator":
            self.communicator = value.lower() == "true"
        elif key == "camera":
            self.camera = value.lower() == "true"
        elif key == "lights":
            self.lights = value.lower() == "true"
        elif key == "set-speed":
            self.speed = float(value)
        elif key == "set-altitude":
            self.altitude = float(value)
        elif key == "check-battery":
            print(f"Drone {self.drone_id} battery level: {self.battery}%")
        elif key == "emergency-land":
            self.emergency_land()
        elif key == "toggle-camera":
            self.camera = not self.camera
        elif key == "toggle-lights":
            self.lights = not self.lights
        # Add more elif blocks for other commands

    def emergency_land(self):
        # Simulate emergency landing
        print(f"Drone {self.drone_id} is performing an emergency landing.")

    async def subscribe_to_commands(self):
        # Subscribe to incoming commands and process them
        while True:
            try:
                command = await self.node.get(f"command-{self.drone_id}", ttl=60, tpf=10, ttp=5)
                if command:
                    await self.process_command(command)
            except Exception as e:
                logging.error(f"Error receiving command: {e}")
                await asyncio.sleep(1)

    async def run(self):
        # Start the node on a specific port and run the main functionalities of the drone
        logging.info(f"Starting drone {self.drone_id} on port {self.port}")
        await self.node.start(port=self.port, dport=33334, ttl=60, tpf=10, client={"name": self.drone_id, "labels": ["data"], "ttp": 5})
        await asyncio.gather(
            self.update_sensors(),
            self.subscribe_to_commands(),
        )
    
def get_port():
    # Get the port from a command-line argument or environment variable
    if len(sys.argv) > 1:
        return int(sys.argv[1])
    else:
        return int(os.environ.get('DRONE_PORT', 33333))

async def main():
    # Main function to create drones and start their operations
    port = get_port()
    logging.info(f"Starting main function with port {port}")
    drone = Drone("drone1", port)
    await drone.run()

if __name__ == "__main__":
    asyncio.run(main())
