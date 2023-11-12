import asyncio
import random
from tcdicn import Server

class Drone:
    def __init__(self, server, drone_id):
        self.server = server
        self.drone_id = drone_id
        self.position = (0, 0)    # Initial position (x, y)
        self.temperature = 20     # Initial temperature in Celsius
        self.battery = 100        # Initial battery percentage
        self.power_usage = 5      # Power usage in percentage per tick
        self.enabled = True       # Drone enabled status
        self.fleet_speed = 1.0    # Fleet speed
        self.altitude = 0         # Altitude

    async def update_sensors(self):
        while True:
            if self.enabled:
                # Simulate sensor reading changes
                self.position = (self.position[0] + random.uniform(-0.1, 0.1),
                                 self.position[1] + random.uniform(-0.1, 0.1))
                self.temperature += random.uniform(-0.5, 0.5)
                self.battery -= self.power_usage / 100

                # Publish sensor readings
                await self.server.set(f"{self.drone_id}-position", str(self.position))
                await self.server.set(f"{self.drone_id}-temperature", str(self.temperature))
                await self.server.set(f"{self.drone_id}-battery", str(self.battery))

            # Wait a bit before next update
            await asyncio.sleep(5)

    async def process_command(self, command):
        key, value = command.split('=')
        
        if key == "enable-drone":
            self.enabled = value.lower() == "true"
        elif key == "fleet-speed":
            self.fleet_speed = float(value)
        elif key == "check-battery":
            print(f"Drone {self.drone_id} battery level: {self.battery}%")
        elif key == "set-altitude":
            self.altitude = float(value)
        elif key == "emergency-land":
            self.emergency_land()
        # Add more elif blocks for other commands

    async def subscribe_to_commands(self):
        while True:
            try:
                command = await self.server.get(f"command-{self.drone_id}")
                if command:
                    print(f"Received command for {self.drone_id}: {command}")
                    await self.process_command(command)
            except Exception as e:
                logging.error(f"Error receiving command: {e}")
                await asyncio.sleep(1)  # Wait before retrying in case of error

    async def run(self):
        await asyncio.gather(
            self.update_sensors(),
            self.subscribe_to_commands(),
        )

async def main():
    server = Server(port=33333, announce_interval=60, peer_timeout=180)
    drone = Drone(server, "drone06")
    await server.start()
    await drone.run()

if __name__ == "__main__":
    asyncio.run(main())
