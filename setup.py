from setuptools import setup

setup(
    name="bifrost-python-lib",
    version="v0.2.0",
    package=["chainpy", "rbcevents"],
    install_requires=["cryptography", "ecdsa", "eth-abi", "eth-account", "pysha3", "requests", "dataclasses-json"]
)
