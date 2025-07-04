import socket
import ssl
import threading
from typing import List

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"


class Client:

    def __init__(self, username, socket):
        self.username = username
        self.socket = socket


class ChatServer:

    def __init__(self, server_ip="localhost", server_port=8888):
        self.server_ip = server_ip
        self.server_port = server_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.total_users: List[Client] = []

        # load ssl certs
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

    def bind_n_listen(self):
        self.server_socket.bind((self.server_ip, self.server_port))
        self.server_socket.listen()

    def accept_clients(self):
        print("Server is listening")
        while True:
            conn, addr = self.server_socket.accept()

            # Wrap the accepted client connection
            secure_conn = self.context.wrap_socket(conn, server_side=True)
            thread = threading.Thread(target=self.handle_client,
                                      args=(secure_conn, addr),
                                      daemon=True)
            thread.start()

    def handle_client(self, conn, addr):
        with conn:
            print(f"connected from {addr}")
            username = conn.recv(1024)
            if username:
                client_obj = Client(username.decode(), conn)
                self.total_users.append(client_obj)
                conn.sendall(b"SERVER:SUCCESS")
                if len(self.total_users) > 1:
                    self.send_total_users(client_obj)
                self.send_connection_msg(client_obj, "connect")
            else:
                return
            while True:
                data = conn.recv(1024)
                print("data recv:", data.decode())
                if not data:  # if len of data sent is 0 -> means use disconnected
                    print(f"disconnected from {addr}")
                    self.send_connection_msg(client_obj, "disconnect")
                    self.total_users.remove(client_obj)
                    break
                if data != " ":
                    self.send_msg_to_all(client_obj, data)

    def send_total_users(self, client_obj_to_send_to):
        msg = [
            f"{user.username} from {user.socket.getpeername()[0]}"
            for user in self.total_users
            if user.socket.fileno() != client_obj_to_send_to.socket.fileno()
        ]
        client_obj_to_send_to.socket.sendall(
            f"SERVER: {GREEN}TOTAL USERS CONNECTED:\n{RESET}{RED}{'\n'.join(msg)} {RESET}"
            .encode())

    def send_msg_to_all(self, client_obj_sending, msg: bytes):
        for user_obj in self.total_users:
            user_socket = user_obj.socket
            # using `fileno()` on a socket object to return the sockets file descriptor number, which is a low-level integer used by the operating system to identify the socket
            if user_socket.fileno() != client_obj_sending.socket.fileno():
                full_message = (
                    f"{RED}{client_obj_sending.username}:{RESET} {msg.decode()}"
                )
                user_socket.sendall(full_message.encode())

    def send_connection_msg(self, client_obj, status: str):
        if status == "connect":
            msg = f"{GREEN}{client_obj.username} connected from {client_obj.socket.getpeername()[0]} {RESET}"
        elif status == "disconnect":
            msg = f"{GREEN}{client_obj.username} disconnected {RESET}"
        else:
            msg = "something went wrong"
        for user_obj in self.total_users:
            user_socket = user_obj.socket
            if user_socket.fileno() != client_obj.socket.fileno():
                user_socket.sendall(f"SERVER: {msg}".encode())

    def clean_close(self):
        # close all user sockets
        for user_obj in self.total_users:
            user_obj.socket.sendall(b"SERVER:CLOSE")
            user_obj.socket.close()
        self.server_socket.close()
        print("\nclosed socket server cleanly")
        return


chat_server = None

try:
    chat_server = ChatServer()
    chat_server.bind_n_listen()
    chat_server.accept_clients()
except KeyboardInterrupt:
    if chat_server:
        chat_server.clean_close()
