from setuptools import setup, find_packages
from chainpy.__init__ import __version__

setup(
    name="chainpy",
    version=__version__,
    package=find_packages,
    install_requires=[
        "eth-abi==2.2.0",
        "eth-keys==0.3.4",
        "eth-account==0.5.9",
        "requests==2.28.1",
        "dataclasses-json==0.5.7",
        "prometheus-client==0.15.0",
        "bridgeconst @ git+https://github.com/bifrost-platform/solidity-contract-configs@0.2.1",
        "python-dotenv==0.16.0",
        "jsonpath-ng"
    ]
)
