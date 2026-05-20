import socket
import logging
from threading import Thread

from core import install_srv6_path

logger = logging.getLogger(__name__)

HELP_MESSAGE = """\
help                                print this message
paths <prefix> <policy> <num>       request <num> paths for <prefix>, satisfying <policy>
install <path_no>                   install the <path_no> from previously requested paths

policies: trusted_paths
          minimize_untrusted
          minimize_rtt (returns only one path)
"""

# Thanks to gemini
def serve_client(conn, addr, messager):
    logger.info(f"New connection from {addr}")
    conn.sendall(b"--- Background Service Console ---\nType 'help' for commands.\n> ")

    last_requested = None

    try:
        while True:
            # Receive data and strip newline characters (Telnet sends \r\n)
            # This way of receiving stuff is not right but we'll pretend it is
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
                    paths = messager.request_path(prefix, policy, num)

                    last_requested = (prefix, paths)

                    pretty_paths = []
                    for path in paths:
                        pretty_paths.append([asn for asn, _ in path])

                    response = "\n".join([f"{num}: {path}" for num, path in enumerate(pretty_paths)])

                except Exception as e:
                    logger.debug(f"Something went wrong while sending the request: {e}")

            elif tokens[0] == 'install':

                logger.info("User requested to install a new SRv6 rule")

                if last_requested is None:
                    response = "Need to request some paths first with 'paths' command"
                else:
                    path_no = int(tokens[1])

                    last_requested_dest, last_requested_paths = last_requested
                    if path_no > len(last_requested_paths):
                        response = "Invalid path number"
                    else:
                        logger.debug(f"Attempting to install a new SRv6 rule for {last_requested_dest}")
                        install_srv6_path(last_requested_dest, last_requested_paths[path_no])
                        response = f"SRv6 rule for {last_requested_dest} installed"

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

class LocalSocketInterfaceThread(Thread):

    def __init__(self, address, port, messager):
        super().__init__()
        self.address = address
        self.port = port
        self.messager = messager

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Re-use port immediately after restart
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.address, self.port))
        server.listen(1)
        # i wonder if logging correctly works
        logger.info(f"Socket for interactive interface started on {self.address}:{self.port}")

        while True:
            conn, addr = server.accept()
            # Serve one client at a time (do not use additional threads)
            serve_client(conn, addr, self.messager)
