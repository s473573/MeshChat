"""
Cryptography related utility functions
"""

from typing import Set
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def read_private_key():
    with open(".key/self", 'rb') as f:
        return serialization.load_pem_private_key(f.read(), None, default_backend())


def read_public_key():
    with open(".key/self.pub", 'rb') as f:
        return serialization.load_ssh_public_key(f.read(), default_backend())


# # * will be writing these before accepting, adding in a nice settings menu
# def append_known_key(key: bytes):
#     with open(".key/known_keys", 'ab') as f:
#         _write_key(f, key)


# def write_known_keys(keys: List[bytes]):
#     with open(".key/known_keys", 'wb') as f:
#         for pubkey in keys:
#             _write_key(f, pubkey)


def read_trusted_keys() -> Set[bytes]:
    with open(".key/trusted", 'rb') as f:
        keys_bytes = f.read()
        return set(keys_bytes.splitlines())


def write_trusted_key(pubkey: bytes):
    with open(".key/trusted", 'ab') as f:
        f.write(pubkey)
        f.write(b'\n')


def get_public_key() -> bytes:
    with open(".key/self.pub", 'rb') as f:
        return f.read()


# def get_known_keys() -> List:
#     with open(".key/known_keys") as f:
#         return f.read().splitlines()


# def read_peer_public_key():
#     with open(".key/known_keys", 'rb') as f:
#         return serialization.load_ssh_public_key(f.read(), default_backend())


def create_keys():
    # write private to keys/self
    # write public to keys/self.pub
    # * later other nodes keys.. (database?)
    # ? .. and comments for each key to differentiate?

    privkey = ed25519.Ed25519PrivateKey.generate()
    privbytes = privkey.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open('.key/self', 'wb') as f:
        f.write(privbytes)

    pubkey = privkey.public_key()
    pubbytes = pubkey.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )
    with open('.key/self.pub', 'wb') as f:
        f.write(pubbytes)

    # return pubbytes
