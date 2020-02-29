#!/usr/bin/env python3
import socket, os, sys, json, select
from queue import Queue


class Client:
    def __init__(self, skt_dir="~/.sockets"):
        self.skt_dir = os.path.abspath(os.path.expanduser(skt_dir))
        print(f"Socket handle directory: {self.skt_dir}")

        self.hndshk_ident = "hndshk"
        self.ident = None
        self.conn = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.rx_queue = Queue()

        if not os.path.exists(os.path.join(self.skt_dir, self.hndshk_ident)):
            print("Server doesn't appear to be running. Exiting.")
            sys.exit()

    def __enter__(self):
        self.__connect()
        return self

    def __exit__(self, *a):
        self.send_command("close_connection")
        self.conn.close()

    def __connect(self):
        hndshk_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        hndshk_sock.connect(os.path.join(self.skt_dir, self.hndshk_ident))
        self.ident = hndshk_sock.recv(32).decode("utf-8")
        hndshk_sock.close()
        print(f'Opened connection with ident "{self.ident}".')

    def send_command(self, cmd):
        return self.__send({"cmd": cmd})

    def send_message(self, msg):
        return self.__send({"msg": msg})

    def __send(self, data):
        json_data = bytes(json.dumps({"payload": data}, separators=(",", ":")), "utf-8")
        return self.conn.sendto(json_data, os.path.join(self.skt_dir, self.ident))

    # TODO Need to thread this recv function
    def recv_worker(self):
        while self.is_active():
            self.conn.settimeout(0.2)
            try:
                raw_data = self.conn.recv(4096).decode("utf-8")
            except socket.timeout:
                continue

            self.conn.settimeout(None)
            data = json.loads(raw_data)
            data.update({"ident": self.ident})
            self.rx_queue.put(data)

    def recv(self):
        raw_data, server = self.conn.recvfrom(4096).decode("utf-8")
        print("Client received: ", raw_data, " from ", server)
        return raw_data

