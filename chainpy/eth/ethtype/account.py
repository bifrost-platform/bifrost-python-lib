import random
import unittest
from typing import Union

from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend
from eth_keys.constants import SECPK1_N
from eth_keys.datatypes import PrivateKey, PublicKey, Signature, NonRecoverableSignature
from eth_utils import keccak

from .hexbytes import EthAddress, EthHexBytes, EthHashBytes

NATIVE_KEY_API = KeyAPI(backend=NativeECCBackend())


class EthAccount:
    def __init__(self, private_key: PrivateKey):
        self._private_key_obj: PrivateKey = private_key
        self._public_key_obj = None
        self._address = None

    @classmethod
    def generate(cls):
        rand_num = random.randint(1, SECPK1_N)
        private_key_obj = NATIVE_KEY_API.PrivateKey(rand_num.to_bytes(32, "big"))
        return cls(private_key_obj)

    @classmethod
    def from_secret(cls, secret: Union[bytearray, bytes, int, str]):
        secret_bytes = EthHexBytes(secret, 32)
        if secret_bytes == 0:
            raise Exception("Zero private key")
        private_key_obj = NATIVE_KEY_API.PrivateKey(EthHexBytes(secret, 32).bytes())
        return cls(private_key_obj)

    @property
    def private_key(self) -> PrivateKey:
        return self._private_key_obj

    @property
    def public_key(self) -> PublicKey:
        if self._public_key_obj is None:
            self._public_key_obj = self._private_key_obj.public_key
        return self._public_key_obj

    @property
    def address(self) -> EthAddress:
        if self._address is None:
            self._address = EthAddress(self.public_key.to_address())
        return self._address

    def ecdsa_sign(self, msg: bytes) -> NonRecoverableSignature:
        return self._private_key_obj.sign_msg_non_recoverable(msg)

    def ecdsa_sign_on_digest(self, msg_digest: bytes) -> NonRecoverableSignature:
        return self._private_key_obj.sign_msg_hash_non_recoverable(msg_digest)

    def ecdsa_recoverable_sign(self, msg: bytes, chain_id: int = None) -> Signature:
        return self._private_key_obj.sign_msg(msg)

    def ecdsa_recoverable_sign_on_digest(self, msg_digest: bytes):
        return self._private_key_obj.sign_msg_hash(msg_digest)

    @staticmethod
    def ecdsa_verify_by_msg(msg: bytes, r: int, s: int, public_key_obj: PublicKey) -> bool:
        sig = NonRecoverableSignature(rs=(r, s))
        return public_key_obj.verify_msg(msg, sig)

    @staticmethod
    def ecdsa_verify_by_digest(msg_digest: bytes, r: int, s: int, public_key_obj: PublicKey) -> bool:
        sig = NonRecoverableSignature(rs=(r, s))
        return public_key_obj.verify_msg_hash(msg_digest, sig)

    @classmethod
    def ecdsa_recover_address(cls, r: int, s: int, v: int, msg: bytes) -> EthAddress:
        if v > 1:
            v = (v + 1) % 2
        sig = Signature(vrs=(v, r, s))
        public_key = sig.recover_public_key_from_msg(msg)
        return EthAddress(public_key.to_address())

    @classmethod
    def ecdsa_recover_address_with_digest(cls, r: int, s: int, v: int, msg_digest: bytes) -> EthAddress:
        if v > 1:
            v = (v + 1) % 2
        sig = Signature(vrs=(v, r, s))
        public_key = sig.recover_public_key_from_msg_hash(msg_digest)
        return EthAddress(public_key.to_address())


class TestEthAccount(unittest.TestCase):
    def setUp(self) -> None:
        self.test_private = 100
        self.expected_address = "0xd9A284367b6D3e25A91c91b5A430AF2593886EB9"
        self.acc: EthAccount = EthAccount.from_secret(self.test_private)

        self.msg = "message".encode()
        self.sig_r = EthHashBytes(0x1359a4a0670e0b2d8fe43c68c724672f1d016d53cf0715b13cacc88827c284ca)
        self.sig_s = EthHashBytes(0x06e210927262217fa714f62c683106d3bd25c4e2bbd4c908f427df24824ce7b6)
        self.sig_bytes = self.sig_r + self.sig_s

    def test_init(self):
        self.assertEqual(int(self.acc.private_key.to_hex(), 16), self.test_private)
        self.assertEqual(self.acc.address, self.expected_address)

    def test_ecdsa(self):
        # basic ecdsa
        sig_basic = self.acc.ecdsa_sign(self.msg)
        self.assertTrue(isinstance(sig_basic, NonRecoverableSignature))
        self.assertTrue(EthAccount.ecdsa_verify_by_msg(self.msg, sig_basic.r, sig_basic.s, self.acc.public_key))

        # recoverable_verify
        sig_recover = self.acc.ecdsa_recoverable_sign(self.msg)
        self.assertTrue(isinstance(sig_basic, NonRecoverableSignature))

        recovered_address = EthAccount.ecdsa_recover_address(sig_recover.r, sig_recover.s, sig_recover.v, self.msg)
        self.assertEqual(recovered_address, self.acc.address)

        msg_digest = keccak(self.msg).digest()
        recovered_address = EthAccount.ecdsa_recover_address_with_digest(
            sig_recover.r, sig_recover.s, sig_recover.v, msg_digest
        )
        self.assertEqual(recovered_address, self.acc.address)
