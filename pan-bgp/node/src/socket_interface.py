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

HELP_MESSAGE = """\
help                                print this message
paths <prefix> <policy> <num>       request <num> paths for <prefix>, satisfying <policy>

policies: trusted_paths
"""

# This way of getting config info can break everything
HOST = config_data['interactive_interface']['address']
PORT = config_data['interactive_interface']['port']

controller = controller_interface.Controller()

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
                policy = tokens[2]
                num = int(tokens[3])
                try:
                    logger.debug(f"Requesting {num} pahts for {prefix} with policy {policy}")
                    paths = controller.request_path(prefix, policy, num)
                    response = f"Paths for prefix {prefix}: {paths}"
                except Exception as e:
                    logger.debug(f"Something went wrong while sending the request: {e}")
            elif tokens[0] == 'help':
                response = HELP_MESSAGE
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

# Why this is here?
def start() -> threading.Thread:
    thread = threading.Thread(target=accept_connections)
    thread.start()
    return thread
