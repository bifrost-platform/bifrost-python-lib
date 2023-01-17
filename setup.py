from setuptools import setup, find_packages
from chainpy.__init__ import __version__

setup(
    name="chainpy",
    version=__version__,
    package=find_packages,
    install_requires=[
        "eth-abi",
        "eth-keys",
        "eth-account",
        "pycryptodome",
        "requests",
        "dataclasses-json",
        "prometheus-client",
        "bridgeconst @ git+https://github.com/bifrost-platform/solidity-contract-configs@230117"
    ]
)
