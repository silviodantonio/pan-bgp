import socket
import threading
import logging

import controller as ctrl

logger = logging.getLogger(__name__)

HELP_MESSAGE = """\
help                                print this message
paths <prefix> <policy> <num>       request <num> paths for <prefix>, satisfying <policy>

policies: trusted_paths
"""

# Thanks to gemini
def serve_client(conn, addr, controller):
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

def accept_connections(address, port, controller):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Re-use port immediately after restart
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((address, port))
    server.listen(1)
    logger.info(f"Socket for interactive interface started on {address}:{port}")

    while True:
        # This is a waiting point
        conn, addr = server.accept()
        # Serve one client at a time
        serve_client(conn, addr, controller)

# I don't want to pass the controller here, temporary fix
def start(address, port, controller: ctrl.Controller) -> threading.Thread:
    thread = threading.Thread(target=accept_connections, args=(address, port, controller,))
    thread.start()
    return thread
