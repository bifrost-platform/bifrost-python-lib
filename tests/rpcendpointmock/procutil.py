import psutil


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
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):   #예외처리
            pass
    return killed


if __name__ == "__main__":
    kill_by_file_name("tests/rpcendpointmock/rpcserver.py")
