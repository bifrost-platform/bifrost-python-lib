from setuptools import setup, find_packages
from chainpy.__init__ import __version__
setup(
    name="bifrost-python-lib",
    version=__version__,
    package=find_packages,
    install_requires=["cryptography", "ecdsa", "eth-abi", "eth-account", "pycryptodome", "requests", "dataclasses-json"]
)
