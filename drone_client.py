import asyncio
from tcdicn import Node

class DroneClient:
    def __init__(self, port, dport):
        self.node = Node()
        self.port = port
        self.dport = dport

    async def send_command(self, drone_id, command):
        # Send a command to a specific drone
        await self.node.set(f"command-{drone_id}", command)
        print(f"Sent command '{command}' to drone {drone_id}")

    async def listen_to_drone_data(self, drone_id):
        # Listen to data published by a specific drone
        while True:
            data = await self.node.get(f"{drone_id}-data", ttl=60, tpf=10, ttp=5)
            print(f"Received data from drone {drone_id}: {data}")

    async def start(self):
        # Start the client node
        await self.node.start(port=self.port, dport=self.dport, ttl=60, tpf=10)
        print(f"Client started on port {self.port} and discovery port {self.dport}")

async def main():
    client = DroneClient(port=33334, dport=33334)
    await client.start()

    # Example commands
    await client.send_command("drone1", "camera=true")
    await client.send_command("drone1", "set-speed=5.0")

    # Listen to drone data (this will run indefinitely)
    await client.listen_to_drone_data("drone1")

if __name__ == "__main__":
    asyncio.run(main())