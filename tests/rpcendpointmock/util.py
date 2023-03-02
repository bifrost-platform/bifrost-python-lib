import copy
import os
from time import sleep

import psutil


def change_block_verbosity(block: dict) -> dict:
    block_clone = copy.deepcopy(block)

    transactions = block_clone["transactions"]
    if len(transactions) == 0 or isinstance(transactions[0], str):
        return block_clone
    else:
        tx_hash_list = list()
        for tx_dict in transactions:
            tx_hash_list.append(tx_dict["hash"])
        block_clone["transactions"] = tx_hash_list
        return block_clone


def kill_by_file_name(file_name: str) -> bool:
    killed = False
    for proc in psutil.process_iter():
        try:
            process_name = proc.name()
            process_id = proc.pid

            if process_name.startswith("Python"):
                command_line = proc.cmdline()

                if file_name in command_line:
                    parent_pid = process_id
                    parent = psutil.Process(parent_pid)

                    for child in parent.children(recursive=True):
                        child.kill()
                    parent.kill()
                    killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return killed


def launch_mock_server(server_launch_file_name: str):
    if kill_by_file_name(server_launch_file_name):
        print("[UnitTest] The server already exists -> killed it and relaunch the server")
    os.system("python {} &".format(server_launch_file_name))
    sleep(3)
    print("The server launched")


if __name__ == "__main__":
    kill_by_file_name("tests/rpcendpointmock/rpcserver.py")
