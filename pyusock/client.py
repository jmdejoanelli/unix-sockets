#!/usr/bin/env python3
import socket, os, sys, json, select


class Client:
    def __init__(self):
        self.srv_ident = "hndshk"
        self.skt_dir = "/home/josef/sockets"
        self.ident = None
        self.conn = None

        if not os.path.exists(os.path.join(self.skt_dir, self.srv_ident)):
            print("Server doesn't appear to be running. Exiting.")
            sys.exit()

    def connect(self):
        hndshk_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        hndshk_sock.connect(os.path.join(self.skt_dir, self.srv_ident))
        self.ident = hndshk_sock.recv(16).decode("utf-8")

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(os.path.join(self.skt_dir, self.ident))
        sock.listen()
        hndshk_sock.send(b"OK\n")
        hndshk_sock.close()
        self.conn, _ = sock.accept()
        print(f'Opened connection with ident "{self.ident}".')

    def send(self, data):
        return self.conn.send(
            bytes(json.dumps({"payload": data}, separators=(",", ":")) + "\n", "utf-8")
        )

    def recv(self):
        raw_data = self.conn.recv(512).decode("utf-8")
        ready = select.select([self.conn], [], [], 0.5)
        if ready[0]:
            raw_data = self.conn.recv(512).decode("utf-8")

        while not raw_data.endswith("\n"):
            ready = select.select([self.conn], [], [], 0.5)
            if ready[0]:
                raw_data = self.conn.recv(512).decode("utf-8")

