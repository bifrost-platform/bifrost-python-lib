from setuptools import setup, find_packages
from chainpy.__init__ import __version__

setup(
    name="chainpy",
    version=__version__,
    package=find_packages,
    install_requires=[
        "eth-abi==2.2.1",
        "eth-keys==0.4.0",
        "eth-account==0.8.0",
        "pycryptodome==3.16.0",
        "requests==2.28.2",
        "dataclasses-json==0.5.7",
        "prometheus-client==0.15.0",
        "bridgeconst @ git+https://github.com/bifrost-platform/solidity-contract-configs@0.2.1",
        "python-dotenv==0.21.0"
    ]
)
