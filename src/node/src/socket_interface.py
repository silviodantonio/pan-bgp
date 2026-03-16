import socket
import threading
import logging

import config
import controller_interface

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
file_handler = logging.FileHandler("/var/log/pangbp.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

config_data = config.load_config_file("/etc/panbgp/node.conf")

# This way of getting config info can break everything
HOST = config_data['interactive_interface']['address']
PORT = config_data['interactive_interface']['port']

# Thanks to gemini
def serve_client(conn, addr):
    logger.info(f"New connection from {addr}")
    conn.sendall(b"--- Background Service Console ---\nType 'help' for commands.\n> ")

    try:
        while True:
            # Receive data and strip newline characters (Telnet sends \r\n)
            data = conn.recv(1024).decode('utf-8').strip()
            tokens = data.split(' ')

            if not tokens or tokens[0] in ['exit', 'quit']:
                conn.sendall(b"Goodbye!\n")
                break

            # Commands
            if tokens[0] == 'paths':
                prefix = tokens[1]
                paths = controller_interface.request_path(prefix)
                response = f"requested paths for prefix {prefix}: {paths}"
            elif tokens[0] == 'help':
                response = "paths <prefix>"
            else:
                response = f"Unknown command: {tokens[0]}"

            # Send response and the prompt for the next command
            conn.sendall(response.encode('utf-8') + b"\n> ")

    except ConnectionResetError:
        logger.info(f"Connection lost from {addr}")
    finally:
        conn.close()

def accept_connections():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Re-use port immediately after restart
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    logger.info(f"Socket for interactive interface started on {HOST}:{PORT}")

    while True:
        # This is a waiting point
        conn, addr = server.accept()
        # Serve one client at a time
        serve_client(conn, addr)

def start() -> threading.Thread:
    thread = threading.Thread(target=accept_connections)
    thread.start()
    return thread
