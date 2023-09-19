from setuptools import setup, find_packages

from chainpy.__init__ import __version__

setup(
    name="chainpy",
    version=__version__,
    package=find_packages,
    install_requires=[
        "eth-abi==4.2.1",
        "eth-keys==0.4.0",
        "eth-account==0.9.0",
        "requests==2.31.0",
        "dataclasses-json==0.6.0",
        "prometheus-client==0.17.1",
        "bridgeconst @ git+https://github.com/bifrost-platform/solidity-contract-configs@0.2.12",
        "python-dotenv==1.0.0",
        "jsonpath-ng==1.6.0",
        "jsonrpcserver",
        "fastapi",
        "uvicorn",
        "psutil",
        "web3==6.9.0"
    ]
)
