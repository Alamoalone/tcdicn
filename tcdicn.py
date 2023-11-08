import asyncio
import json
import logging
import socket
import time
from asyncio import DatagramTransport, StreamWriter, StreamReader, Task
from typing import Tuple, Dict


VERSION = "0.1"


# Utility class for storing the address (host and port number) of peers in a useful structure
class _Address:

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def __eq__(self, other):
        return self.host == other.host and self.port == other.port

    def __hash__(self):
        return hash((self.host, self.port))

    def __str__(self):
        return f"{self.host}:{self.port}"


# Provides all the networking logic for interacting with a network of TCD ICN nodes
class Server:

    # Initialise server
    def __init__(self, port: int,  announcement_interval: int, peer_timeout_interval: int):
        self.port = port  # Port number to listen on and send requests to
        self.announcement = self._create_announcement_msg()  # Bytes to send as announcement
        self.announcement_interval = announcement_interval  # Seconds between each announcement
        self.peer_timeout_interval = peer_timeout_interval  # Seconds without announcement until a peer is forgotten
        self.peers: Dict[_Address, Task] = dict()  # Cache of peers whose announcement we have recently heard
        self.dataset = dict()  # Local named data cache

    # Start the server as a coroutine
    # Cancel the coroutine to shutdown the server gracefully
    async def start(self):
        logging.info(f"Listening on port :{self.port}")
        try:
            await asyncio.gather(self._start_udp_server(), self._start_tcp_server())
        except OSError as e:
            logging.error(f"Server error: {e}")
        except asyncio.exceptions.CancelledError:
            logging.warning(f"Server tasks cancelled")

    # Retrieve named data from the ICN network
    # This does not actually do any networking but just looks up what is in the local cache
    async def get(self, name: str):
        return self.dataset[name]["value"] if name in self.dataset else "unknown"

    # Publish named data to the ICN network
    # The data will be pushed to all known peers, who will push to all their known peers, etc...
    async def set(self, name: str, value: str):
        self.dataset[name] = { "value": value, "time": time.time() }
        await self._send_to_addrs(self._create_set_msg(name), self.peers.keys())

    # Methods below here are "private" and should not be used directly by applications

    # Listen for and regularly broadcast peer announcements to let other nodes know we exist
    async def _start_udp_server(self):
        logging.debug("Creating UDP server...")
        # Listen for announcements
        class Protocol:
            def connection_made(_, transport: DatagramTransport):
                logging.debug(f"UDP transport established: {transport}")
            def connection_lost(_, e: Exception):
                logging.warning(f"UDP transport lost: {e}")
            def datagram_received(_, data: bytes, addr: Tuple[str, int]):
                self._on_udp_datagram(data, _Address(*addr[0:2]))
            def error_received(_, e: OSError):
                logging.warning(f"UDP transport error: {e}")
        transport, protocol = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: Protocol(), local_addr=("0.0.0.0", self.port), allow_broadcast=True)
        # Regularly broadcast announcements
        while True:
            logging.debug("Sending peer announcement...")
            transport.sendto(self.announcement, ("<broadcast>", self.port))
            await asyncio.sleep(self.announcement_interval)

    # If we receive an announcement from a peer, add its address to our peer cache with an expiry timer
    # If it is already in our peer cache, reset its expiry timer
    def _on_udp_datagram(self, data: bytes, addr: _Address):
        # Ignore own announcements, adapted from https://gist.github.com/bennr01/7043a460155e8e763b3a9061c95faaa0
        local_addrs = socket.getaddrinfo(socket.gethostname(), self.port)
        remote_addrs = socket.getaddrinfo(socket.getfqdn(addr.host), addr.port)
        for (_, _, _, _, local_addr) in local_addrs:
            for (_, _, _, _, remote_addr) in remote_addrs:
                if remote_addr == local_addr:
                    return
        # Ignore malformed announcements
        if data != self.announcement:
            return
        # Cancel previous expiry timer
        logging.debug(f"Received peer announcement from {addr}.")
        if addr in self.peers:
            self.peers[addr].cancel()
        else:
            logging.info(f"Added new peer: {addr}.")
        # Insert new peer address and expiry timer
        async def _do_peer_timeout():
            await asyncio.sleep(self.peer_timeout_interval)
            logging.info(f"Removed timed-out peer: {addr}.")
            del self.peers[addr]
        self.peers[addr] = asyncio.create_task(_do_peer_timeout())

    # Start listening for peer connecting to get or set named data on the network
    async def _start_tcp_server(self):
        logging.debug("Creating TCP server...")
        server = await asyncio.start_server(self._on_tcp_connection, None, self.port)
        await server.serve_forever()

    # Handle peer connection
    async def _on_tcp_connection(self, reader: StreamReader, writer: StreamWriter):
        addr = _Address(*writer.get_extra_info("sockname")[0:2])
        logging.debug(f"Handling TCP connection from {addr}...")
        # Read entire message
        msg_bytes = await reader.read()
        writer.close()
        msg = json.loads(msg_bytes)
        # Ignore invalid messages
        if msg["version"] != VERSION or msg["type"] != "set":
            return
        # Extract name and data
        name = msg["name"]
        data = { "value": msg["value"], "time": msg["time"] }
        # Ignore duplicate messages
        if name in self.dataset and data["time"] <= self.dataset[name]["time"]:
            logging.debug(f"Ignoring duplicate data {name} from {addr}: {data}")
            return
        # Insert new data into data and forward to other peers
        logging.info(f"Received update to data {name} from {addr}: {data}")
        self.dataset[name] = data
        other_addrs = [ peer for peer in self.peers.keys() if peer != addr ]
        await self._send_to_addrs(msg_bytes, other_addrs)

    # Send bytes over TCP to list of addresses
    async def _send_to_addrs(self, msg_bytes: bytes, addrs):
        async def send(addr):
            logging.debug(f"Sending message to {addr}...")
            reader, writer = await asyncio.open_connection(addr.host, addr.port)
            writer.write(msg_bytes)
            writer.close()
        aws = [ asyncio.create_task(send(addr)) for addr in addrs ]
        if len(aws) != 0:
            _, pending = await asyncio.wait(aws, timeout=10)
            if len(pending) != 0:
                [ task.cancel() for task in pending ]
                await asyncio.wait(pending)

    # Construct well-formatted "announcement" message bytes
    def _create_announcement_msg(self):
        return json.dumps({
            "version": VERSION,
            "type": "announcement"
        }).encode()

    # Construct well-formatted "set" message bytes for data
    def _create_set_msg(self, name: str):
        return json.dumps({
            "version": VERSION,
            "type": "set",
            "name": name,
            "value": self.dataset[name]["value"],
            "time": self.dataset[name]["time"]
        }).encode()
