
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
        self.node = Node()  # Node instance for network communication
        self.drone_id = drone_id
        self.port = port
        self.group_name = None  # Group name for encrypted communication

    async def start(self):
        # Generate keypair
        keypair = self.node.generate_keypair()
        
        # Start the node with the keypair
        await self.node.start(keypair)

    async def establish_group(self, group_name):
        self.group_name = group_name
        await self.node.establish(group_name)

    async def invite_to_group(self, client_name, client_public_key):
        if self.group_name:
            await self.node.invite(self.group_name, client_name, client_public_key)

    async def join_group(self, inviter_name, inviter_public_key):
        if self.group_name:
            await self.node.join(self.group_name, inviter_name, inviter_public_key)

    async def get_data(self, label):
        return await self.node.get(label, self.group_name)

    async def set_data(self, label, data):
        await self.node.set(label, data, self.group_name)

# Example usage
if __name__ == '__main__':
    drone = Drone(drone_id='drone1', port=8000)
    asyncio.run(drone.start())
    # Further group establishment, invitation, and joining can be added here
