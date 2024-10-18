from . import util as cu

from typing import Set
from threading import Lock

import socket

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

import logging


logger = logging.getLogger(__name__)
HEADER_SIZE = 4


# initializing only once when importing
private_key: ed25519.Ed25519PrivateKey = cu.read_private_key()
public_bytes: bytes = cu.get_public_key()


class Node:
    def __init__(self, sock: socket.socket, is_client=False, trusted_keys: Set[bytes] = None):
        self.trusted_keys: Set[bytes] = cu.read_trusted_keys()
        if trusted_keys:
            self.trusted_keys |= trusted_keys

        self.node_sock = sock
        self.peer_ipa = sock.getpeername()[0]

        if is_client:
            self._send_msg(public_bytes)
            pubkey_bytes = self._recv_msg()
            if pubkey_bytes not in self.trusted_keys:
                raise RuntimeError("Initial received message is not a known public key")
        else:
            # receive pubic key and check if known
            pubkey_bytes = self._recv_msg()
            if pubkey_bytes not in self.trusted_keys:
                raise RuntimeError("Initial received message is not a known public key")

            self._send_msg(public_bytes)

        self.peer_kbytes = pubkey_bytes
        self.peer_pubkey = serialization.load_ssh_public_key(pubkey_bytes, default_backend())
        # callback to handle messages
        self.dispatcher = lambda _: None
        # can't send asynchronously, key derivation will break. peer would try to process first message and answer with an old key
        self.sending_lock = Lock()

        shared = self.exchange_dh(is_client)
        self.derive_enc_key(shared)

    def send_message(self, msg: bytes):
        """
        Securely transmit a byte message
        """

        self.derive_enc_key(self.enc_key)

        fernet = Fernet(base64.urlsafe_b64encode(self.enc_key))
        msg_token = fernet.encrypt(msg)

        self._send_msg(msg_token)

    def receive_message(self) -> bytes:
        """
        Receive and decrypt a byte message
        """

        msg_token = self._recv_msg()

        # deriving only after received something to avoid messing with send_message
        self.derive_enc_key(self.enc_key)

        fernet = Fernet(base64.urlsafe_b64encode(self.enc_key))
        return fernet.decrypt(msg_token)

    def close(self):
        self.node_sock.shutdown(socket.SHUT_RD)
        self.node_sock.close()
        logger.debug("closed node")

    def _send_msg(self, msg: bytes) -> None:
        logger.debug("sending...")
        self.node_sock.send(len(msg).to_bytes(HEADER_SIZE, byteorder='big'))
        self.node_sock.send(msg)
        logger.debug("message sent")

    def _recv_msg(self) -> bytes:
        logger.debug("waiting for a message")
        msg_len = int.from_bytes(self.node_sock.recv(HEADER_SIZE), byteorder='big')
        msg = b''
        logger.debug("receiving a message...")
        # ! this refused to receive initial neighbours. wtf??
        # while len(msg) < msg_len:
        #     msg += self.node_sock.recv(16)
        msg = self.node_sock.recv(msg_len)
        if not msg:
            raise OSError(f"{self.peer_ipa} closed the connection socket")
        logger.debug("completed receiving a message")
        return msg

    def exchange_dh(self, is_client=False):
        dh_priv = ec.generate_private_key(ec.SECP256K1, default_backend())
        dh_pub = dh_priv.public_key()

        if is_client:
            self._send_dh(dh_pub)
            dh_peer_pub = self._receive_dh()
        else:
            dh_peer_pub = self._receive_dh()
            self._send_dh(dh_pub)

        return dh_priv.exchange(ec.ECDH(), dh_peer_pub)

    def derive_enc_key(self, key):
        self.enc_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=None,
            backend=default_backend()
        ).derive(key)

    def _receive_dh(self) -> ec.EllipticCurvePublicKey:
        logger.debug("DH: waiting for the public key signature...")
        peer_pubsign = self._recv_msg() 

        logger.debug("DH: waiting for the public key...")
        peer_dh_pubbytes = self._recv_msg()

        self.peer_pubkey.verify(peer_pubsign, peer_dh_pubbytes)
        logger.debug("DH: successfully verified the key")

        return default_backend().load_elliptic_curve_public_bytes(ec.SECP256K1, peer_dh_pubbytes)

    def _send_dh(self, dhpk):
        dh_pub_bytes = dhpk.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)

        pubsign = private_key.sign(dh_pub_bytes)
        logger.debug("DH: sending the public key signature...")
        self._send_msg(pubsign)

        logger.debug("DH: sending the public key...")
        self._send_msg(dh_pub_bytes)
