#!/usr/bin/env python3
import socket, threading, random, time, signal, os, json, select
from queue import Queue


class Server:
    def __init__(self):
        signal.signal(signal.SIGINT, self.sigint_handler)

        self.skt_dir = "/home/josef/sockets"
        if not os.path.exists(self.skt_dir):
            os.mkdir(self.skt_dir)

        self.srv_ident = "hndshk"
        self.hndshk_f = os.path.join(self.skt_dir, self.srv_ident)
        self.hndshk_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.hndshk_sock.settimeout(None)
        self.connections = {}

        self.stop_thread = threading.Thread(target=self.stop_worker)
        self.hndshk_thread = threading.Thread(target=self.hndshk_worker)
        self.hndshk_thread.daemon = True

        self.running = False

    def sigint_handler(self, sig, frame):
        print("\nSIGINT caught. Exiting.")
        self.stop()

    def run(self):
        print("Server running. Press ENTER any time to exit.")
        self.hndshk_sock.bind(self.hndshk_f)
        self.hndshk_sock.listen()
        self.hndshk_thread.start()
        self.running = True
        self.stop_thread.start()

        while self.running:
            time.sleep(0.01)

        self.stop()

    def stop(self):
        self.hndshk_sock.close()

        if os.path.exists(os.path.join(self.skt_dir, self.srv_ident)):
            os.remove(self.hndshk_f)

        for ident in self.connections.keys():
            self.close_connection(ident)

        self.connections = {}

        self.stop_thread.join()
        print("Done.")

    def open_connection(self, ident):
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.setblocking(0)
        conn.connect(os.path.join(self.skt_dir, ident))
        self.connections[ident] = {
            "connection": conn,
            "rx_queue": Queue(),
            "rx_thread": threading.Thread(target=self.recv_worker, args=(ident,)),
            "active": True,
        }
        self.connections[ident]["rx_thread"].daemon = True
        self.connections[ident]["rx_thread"].start()

        print(f'Client connection opened on "{ident}"')

    def close_connection(self, ident):
        self.connections[ident]["active"] = False
        self.connections.get(ident).get("connection").close()
        os.remove(os.path.join(self.skt_dir, ident))
        print(f'Client connection closed on "{ident}"')

    def hndshk_worker(self):
        while True:
            print("Waiting for client connection...")
            hndshk_conn, _ = self.hndshk_sock.accept()
            print(f'Connected to new client on "{self.srv_ident}".')

            ident = f"{random.randrange(2**24-1):06x}"
            hndshk_conn.send(bytes(ident, "utf-8"))
            ack = hndshk_conn.recv(16).decode("utf-8") == "OK\n"
            if ack:
                self.open_connection(ident)
            else:
                print("ERROR: Didn't recieve an ack.")
            hndshk_conn.close()

    def stop_worker(self):
        input()
        self.running = False

    def recv_worker(self, ident):
        while self.connections.get(ident).get("active") and self.running:
            conn = self.connections.get(ident).get("connection")
            queue = self.connections.get(ident).get("rx_queue")

            ready = select.select([conn], [], [], 0.5)
            if ready[0]:
                raw_data = conn.recv(512).decode("utf-8")

            while not raw_data.endswith("\n"):
                ready = select.select([conn], [], [], 0.5)
                if ready[0]:
                    raw_data = conn.recv(512).decode("utf-8")

            if raw_data != "":
                queue.put(json.loads(raw_data.rstrip("\n")).get("payload"))

    def send(self, ident, data):
        return (
            self.connections.get(ident)
            .get("connection")
            .send(
                bytes(
                    json.dumps({"payload": data}, separators=(",", ":")) + "\n", "utf-8"
                )
            )
        )
