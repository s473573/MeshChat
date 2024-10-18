from .node import Node, public_bytes
# from .util import write_known_keys, append_known_key

from typing import (List, NamedTuple, Callable, Dict, Set)
from threading import Thread
import socket
from ast import literal_eval

import logging


logging.basicConfig(filename='log', filemode='w', level=logging.DEBUG)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


MESHCHAT_PORT = 8008
MAX_NEIGHBOURS = 4


class Peer(NamedTuple):
    ipa: str
    # should be in bytes to easily construct a public key or decode to str
    kbytes: bytes
    # key: Optional[bytes] = None


# TODO: sort methods logically im seeking looking everywhere cannot find the right one
class Meshchat:

    def __init__(self):
        self.public_bytes = public_bytes
        self.neighbours: List[Peer] = []
        self.known_peers: Dict[bytes, str] = {}

        self.connections: Dict[str, Node] = {}

        self._setup_serversocket()
        self._setup_callbacks()

    def _setup_serversocket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        s.bind(("0.0.0.0", MESHCHAT_PORT))

        self.serv_sock = s

    def _setup_callbacks(self):
        self.on_joined = lambda _: None
        self.on_peer_joined = lambda _: None
        self.on_connected = lambda _: None
        self.on_peer_connected = lambda _: None
        self.on_peer_disconnected = lambda _: None
        self.on_received_peers = lambda _: None

    def bind(self, **kwargs):
        for key, value in kwargs.items():
            assert callable(value), f"{value} is not callable"
            setattr(self, key, value)

    def start_network(self):
        """
        Start hosting new connections
        """

        self.serve_thread = Thread(target=self.serve_peers)
        self.serve_thread.start()

    def listen_peer(self):
        self.serv_sock.listen(1)
        client_socket, address = self.serv_sock.accept()
        ipa = address[0]

        node = Node(sock=client_socket, is_client=False, trusted_keys=set(self.known_peers.keys()))

        peer_pubkey = node.peer_kbytes
        # when connecting node already checks if new key is trusted and invited
        if peer_pubkey not in self.known_peers:
            logger.debug(f"{peer_pubkey} is a new invitee, alerting")
            self.alert_newpeer(ipa, peer_pubkey, ipa)
        # * if a peer joins with a new ipa it will be reset
        self.known_peers[peer_pubkey] = ipa

        self._add_neighbour(Peer(ipa, peer_pubkey))

        self.connections[ipa] = node
        msg_listen_thread = Thread(target=self.listen_messages, args=(ipa,))
        msg_listen_thread.start()

        logger.info(f"{ipa}: connection established")
        self.on_peer_connected(node)

    def serve_peers(self):
        # will listen to any messages from known public keys nodes
        while True:
            try:
                self.listen_peer()
            except RuntimeError as e:
                logger.error(repr(e))
                continue
            # socket shut down
            except OSError:
                logger.debug("stopped serving peers")
                break

    def alert_newpeer(self, sender_ipa: str, peer_pubkey: bytes, peer_ipa: str):
        for n in self.neighbours:
            if n.ipa in (peer_ipa, sender_ipa):
                continue
            node = self._get_peer(n.ipa)

            node.send_message(MESSAGE_CODES['newpeer'])
            node.send_message(repr((peer_ipa, peer_pubkey)).encode())

            logger.debug(f"alerted neighbour: {n.ipa} of {peer_ipa}")

    def join_network(self, ipa: str):
        """
        Connect to a network, receiving all network peers from the inviter
        """

        # * catch connect exception here

        self.connect_peer(ipa)
        self.bootstrap(ipa)

        self.serve_thread = Thread(target=self.serve_peers)
        self.serve_thread.start()

        self.on_joined(ipa)

    def connect_peer(self, ipa: str):
        logger.debug(f"connecting to {ipa}")

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ipa, MESHCHAT_PORT))

        node = Node(sock=client_socket, is_client=True, trusted_keys=set(self.known_peers.keys()))
        peer_pubkey = node.peer_kbytes

        self.known_peers[peer_pubkey] = ipa

        # ? rename Peer to Neighbour if it's only used here ?
        self._add_neighbour(Peer(ipa, peer_pubkey))

        self.connections[ipa] = node
        msg_listen_thread = Thread(target=self.listen_messages, args=(ipa,))
        msg_listen_thread.start()

        logger.info(f"{ipa}: connection established")
        self.on_connected(node)

    def bootstrap(self, ipa: str):
        self.request_neighbours(ipa)
        self.request_known_peers(ipa)

    def request_neighbours(self, ipa: str):
        logger.debug(f"requesting neighbours from {ipa}")

        node = self._get_peer(ipa)
        node.sending_lock.acquire()

        node.send_message(MESSAGE_CODES['neighbours'])

    def _get_neighbours(self, node):
        new_neighbours_str = node.receive_message().decode()

        for n in literal_eval(new_neighbours_str):
            # self._add_neighbour(Peer(n[0], n[1]))
            self._add_neighbour(Peer(*n))

        logger.debug(f"neighbours are: {self.neighbours}")
        node.sending_lock.release()

    def _add_neighbour(self, n: Peer):
        assert len(self.neighbours) <= MAX_NEIGHBOURS
        # sockets will close after timeout so i mustn't include reconnections
        if n not in self.neighbours:
            # rotating neighbours deleting the first one
            if len(self.neighbours) == MAX_NEIGHBOURS:
                del self.neighbours[0]
                logger.debug("rotating, removed first neighbour")
            self.neighbours.append(n)

            logger.debug(f"{n.ipa} new neighbour")

    def request_known_peers(self, ipa):
        logger.debug(f"requesting known peers from {ipa}")

        node = self._get_peer(ipa)
        node.sending_lock.acquire()

        node.send_message(MESSAGE_CODES['knownpeers'])

    def _get_known_peers(self, node):
        logger.debug("receiving string..")
        new_peers_str = node.receive_message().decode()

        new_peers = literal_eval(new_peers_str)
        self.known_peers = {**self.known_peers, **new_peers}
        node.sending_lock.release()
        logger.debug(f"received {len(new_peers)} peers")

        self.on_received_peers(node.peer_ipa)

    def set_message_dispatcher(self, ipa: str, _dispatcher: Callable):
        self.connections[ipa].dispatcher = _dispatcher

    def listen_messages(self, ipa: str):
        """
        """

        # * would raise here if ipa is not in connections
        node = self.connections[ipa]

        # ! introduce timeout to waiting message closing the socket and thread after, raise
        # ? also a nice androidtoast-like pop up telling disconnecting due to timeout ?
        while True:
            try:
                msg = node.receive_message()
            # socket is dead
            except OSError:
                break

            if msg == MESSAGE_CODES['neighbours']:
                # i must request before, they can't just control my peer lists
                if node.sending_lock.locked():
                    self._get_neighbours(node)
                else:
                    self._send_neighbours(node)

            elif msg == MESSAGE_CODES['knownpeers']:
                # * could send me knownpeers even when i asked for neighbours
                if node.sending_lock.locked():
                    self._get_known_peers(node)
                else:
                    self._send_known_peers(node)

            elif msg == MESSAGE_CODES['none']:
                node.sending_lock.release()
            elif msg == MESSAGE_CODES['newpeer']:
                self._add_newpeer(node)
            else:
                logger.debug("dispatching regular message...")
                node.dispatcher(msg.decode())

        # if node.sending_lock.locked():
        #     node.sending_lock.release()

        logger.debug(f"stopped listening for messages from {ipa}")
        self.on_peer_disconnected(node)

    def _send_neighbours(self, node):
        neighbours = self.neighbours.copy()

        peer = Peer(node.peer_ipa, node.peer_kbytes) 
        if peer in neighbours:
            neighbours.remove(peer)
        if not neighbours:
            node.send_message(MESSAGE_CODES['none'])
            return

        node.send_message(MESSAGE_CODES['neighbours'])
        node.send_message(repr([tuple(n) for n in neighbours]).encode())

        logger.debug(f"{len(neighbours)} neighbours sent")

    def _add_newpeer(self, node):
        newpeer = literal_eval(node.receive_message().decode())
        ipa = newpeer[0]
        pubkey = newpeer[1]

        if pubkey not in self.known_peers:
            logger.debug(f"added new peer {ipa}...")
            # self.on_peer_joined(Peer(ipa, pubkey))
            self.on_peer_joined(Peer(*newpeer))

            # if i'm not familiar i'm gonna tell my neighbours about this new peer
            self.alert_newpeer(node.peer_ipa, pubkey, ipa)

        # ipa may change, resetting it
        self.known_peers[pubkey] = ipa

    def _send_known_peers(self, node):
        peers = self.known_peers.copy()
        del peers[node.peer_kbytes]

        if not peers:
            node.send_message(MESSAGE_CODES['none'])
            logger.debug("sent none")
            return

        node.send_message(MESSAGE_CODES['knownpeers'])
        node.send_message(repr(peers).encode())
        logger.debug("sent peers")

    def _get_peer(self, ipa: str):
        if ipa not in self.connections:
            self.connect_peer(ipa)
        return self.connections[ipa]

    def send_message(self, ipa: str, msg: str):
        """
        Send a text message to ipa, establish a connection if needed
        """

        node = self._get_peer(ipa)
        with node.sending_lock:
            node.send_message(msg.encode())

    def close_connections(self):
        for ipa in self.connections:
            node = self.connections[ipa]
            node.close()
        self.connections.clear()

    def stop_serving(self):
        self.serv_sock.shutdown(socket.SHUT_RDWR)

    def stop(self):
        self.close_connections()
        self.stop_serving()

    def get_known_peers(self) -> Set[Peer]:
        return {Peer(ipa=item[1], kbytes=item[0]) for item in self.known_peers.items()}

    def get_connections(self) -> Set[Node]:
        return set(self.connections.values())

    def get_known_networks(self) -> List[str]:
        """
        Return ip addresses of all known networks

        :returns: a list containing ip addresses
        """

        try:
            with open('known_networks') as f:
                return f.read().splitlines()
        except FileNotFoundError:
            return []


MESSAGE_CODES = {
    'none': (0).to_bytes(2, byteorder='big'),
    # ? send this when want to get neighbours and when sending ?
    'neighbours': (1).to_bytes(2, byteorder='big'),
    # inform the peer of a new peer in the network
    'newpeer': (2).to_bytes(2, byteorder='big'),
    # send me all your known_peers
    'knownpeers': (4).to_bytes(2, byteorder='big')
}
