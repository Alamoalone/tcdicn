import asyncio
import random
from tcdicn import Server

# Define the drone
class Drone:
    def __init__(self, server, drone_id):
        self.server = server
        self.drone_id = drone_id
        self.position = (0, 0)    # Initial position (x, y)
        self.temperature = 20     # Initial temperature in Celsius
        self.battery = 100        # Initial battery percentage
        self.power_usage = 5      # Power usage in percentage per tick

    async def update_sensors(self):
        while True:
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

    async def subscribe_to_commands(self):
        while True:
            # Subscribe to commands for this drone
            command = await self.server.get(f"command-{self.drone_id}")
            if command:
                # Process command
                print(f"Received command for {self.drone_id}: {command}")
                # Implement command handling logic here

            # Wait a bit before checking for new commands
            await asyncio.sleep(1)

    async def run(self):
        # Start updating sensors and subscribing to commands
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
