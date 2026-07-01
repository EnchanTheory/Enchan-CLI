import subprocess
import ctypes
import sys
import threading
import socket
import time


CREATE_NEW_PROCESS_GROUP = 0x00000200

def listen_for_shutdown(port, p):
    try:
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', port))
        s.listen(1)
        # We only expect one connection ever
        conn, addr = s.accept()
        conn.recv(1024)
        conn.close()
        s.close()
    except Exception:
        pass
    
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.GenerateConsoleCtrlEvent(1, p.pid)
        except Exception:
            pass
    else:
        try:
            p.terminate()
        except Exception:
            pass
    
    # Give it up to 10 seconds to exit gracefully
    try:
        p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/pid", str(p.pid), "/t", "/f"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            p.kill()

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
    
    port = int(sys.argv[1])
    cmd = sys.argv[2:]
    
    popen_kwargs = {}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP
    p = subprocess.Popen(cmd, **popen_kwargs)
    
    t = threading.Thread(target=listen_for_shutdown, args=(port, p), daemon=True)
    t.start()
    
    # Wait for the main process to exit
    p.wait()
    sys.exit(p.returncode)

if __name__ == '__main__':
    main()
