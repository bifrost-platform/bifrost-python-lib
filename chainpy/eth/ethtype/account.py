import random
import unittest
from typing import Union

from eth_keys import KeyAPI
from eth_keys.datatypes import PrivateKey, PublicKey, Signature, NonRecoverableSignature
from eth_keys.backends import NativeECCBackend
from eth_keys.constants import SECPK1_N
from eth_utils import keccak

from .hexbytes import EthAddress, EthHexBytes, EthHashBytes

NATIVE_KEY_API = KeyAPI(backend=NativeECCBackend())

# from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey, EllipticCurvePublicKey
#
# from ecdsa.keys import SigningKey, VerifyingKey
# from cryptography.hazmat.primitives.asymmetric import ec

# from .utils import *


# def convert_singing_key_obj(ecdsa_signing_key: SigningKey) -> EllipticCurvePrivateKey:
#     private_key = EthHexBytes(ecdsa_signing_key.to_string())
#     return ec.derive_private_key(private_key.int(), ec.SECP256K1())
#
#
# def convert_verifying_key_obj(ecdsa_verifying_key: VerifyingKey) -> EllipticCurvePublicKey:
#     encoded_verifying_key = ecdsa_verifying_key.to_string()
#     return EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), encoded_verifying_key)
#
#
# def password_as_bytes(password: Union[str, int, bytes] = None):
#     if password is None:
#         return None
#     if isinstance(password, str):
#         return password.encode()
#     elif isinstance(password, bytes):
#         return password
#     elif isinstance(password, int):
#         return password.to_bytes(32, byteorder="big")
#     else:
#         raise Exception("Not supported password type")


# class WrappedVerifyingKey(VerifyingKey):
#     def __init__(self, curve: Curve, hash_func, pubkey):
#         super().__init__(_error__please_use_generate=True)
#         self.curve = curve
#         self.default_hashfunc = hash_func
#         self.pubkey = pubkey
#
#     @classmethod
#     def from_verifying_key(cls, verifying_key: VerifyingKey):
#         string = verifying_key.to_string()
#         curve = verifying_key.curve
#         hash_func = verifying_key.default_hashfunc
#         point = PointJacobi.from_bytes(
#             curve.curve,
#             string,
#             validate_encoding=True,
#             valid_encodings=None,
#         )
#         pubkey = ecdsa.Public_key(curve.generator, point, True)
#         pubkey.order = curve.order
#         return cls(curve, hash_func, pubkey)
#
#     def hex(self) -> str:
#         vk_bytes = self.to_string()
#         return vk_bytes.hex()
#
#     def bytes(self) -> bytes:
#         return self.to_string()
#
#     def coordinates(self) -> (int, int):
#         vk_hex = self.hex().replace("0x", "")
#         return int(vk_hex[:64], 16), int(vk_hex[64:], 16)
#
#     def ecdsa_verify_msg(self, r: EthHexBytes, s: EthHexBytes, msg: EthHexBytes) -> bool:
#         return super().verify(r + s, msg)
#
#     def ecdsa_verify_hash(self, r: EthHexBytes, s: EthHexBytes, msg_digest: EthHashBytes):
#         return super().verify_digest(r + s, msg_digest)


# class WrappedSignature:
#     def __init__(self, r: EthHexBytes, s: EthHexBytes, v: Optional[int]):
#         if len(r) != 32 or len(s) != 32:
#             raise Exception("Signature size error: r(), s()".format(len(r), len(r)))
#         self.__r: EthHexBytes = r
#         self.__s: EthHexBytes = s
#         self.__v: int = v
#
#     @classmethod
#     def from_sig_ints(cls, r: int, s: int, v: int = None):
#         return cls(EthHexBytes(r, 32), EthHexBytes(s, 32), v)
#
#     def encoded_bytes(self) -> EthHexBytes:
#         return self.__r + self.__s
#
#     @property
#     def r(self) -> int:
#         return self.__r.int()
#
#     @property
#     def s(self) -> int:
#         return self.__s.int()
#
#     @property
#     def v(self) -> int:
#         return self.__v
#
#     def rs(self) -> (int, int):
#         return self.__r.int(), self.__s.int()
#
#     def rsv(self) -> (int, int, int):
#         if self.__v is None:
#             raise Exception("v is none")
#         return self.__r.int(), self.__s.int(), self.__v


class EthAccount:
    def __init__(self, private_key: PrivateKey):
        self.__private_key_obj: PrivateKey = private_key
        self.__public_key_obj = None
        self.__address = None

    @classmethod
    def generate(cls):
        rand_num = random.randint(1, SECPK1_N)
        private_key_obj = NATIVE_KEY_API.PrivateKey(rand_num.to_bytes(32, "big"))
        return cls(private_key_obj)

    @classmethod
    def from_secret(cls, secret: Union[bytearray, bytes, int, str]):
        private_key_obj = NATIVE_KEY_API.PrivateKey(EthHexBytes(secret, 32).bytes())
        return cls(private_key_obj)

    @property
    def priv(self) -> int:
        return int(self.__private_key_obj.to_hex(), 16)

    @property
    def public_key(self) -> PublicKey:
        if self.__public_key_obj is None:
            self.__public_key_obj = self.__private_key_obj.public_key
        return self.__public_key_obj

    @property
    def address(self) -> EthAddress:
        if self.__address is None:
            self.__address = EthAddress(self.public_key.to_address())
        return self.__address

    def ecdsa_sign(self, msg: bytes) -> NonRecoverableSignature:
        return self.__private_key_obj.sign_msg_non_recoverable(msg)

    def ecdsa_sign_on_digest(self, msg_digest: bytes) -> NonRecoverableSignature:
        return self.__private_key_obj.sign_msg_hash_non_recoverable(msg_digest)

    def ecdsa_recoverable_sign(self, msg: bytes, chain_id: int = None) -> Signature:
        return self.__private_key_obj.sign_msg(msg)

    def ecdsa_recoverable_sign_on_digest(self, msg_digest: bytes):
        return self.__private_key_obj.sign_msg_hash(msg_digest)

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
        self.assertEqual(self.acc.priv, self.test_private)
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
