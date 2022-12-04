from setuptools import setup, find_packages

setup(
    name="bifrost-python-lib",
    version="0.3.0",
    package=find_packages,
    install_requires=[
        "cryptography",
        "ecdsa",
        "eth-abi",
        "eth-account",
        "pycryptodome",
        "requests",
        "dataclasses-json"
    ]
)
