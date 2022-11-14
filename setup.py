from setuptools import setup, find_packages

setup(
    name="bifrost-python-lib",
    version="v0.2.0",
    package=find_packages,
    install_requires=["cryptography", "ecdsa", "eth-abi", "eth-account", "pysha3", "requests", "dataclasses-json"]
)
