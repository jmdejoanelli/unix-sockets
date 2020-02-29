#!/usr/bin/env python3
import socket, threading, random, time, signal, os, json, select
from queue import Queue, Empty


class Connection:
    def __init__(self, skt_dir, ident, rx_queue):
        self.ident = ident
        self.skt_dir = skt_dir
        self.conn = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.conn.bind(os.path.join(skt_dir, ident))
        self.active = True
        self.rx_thread = threading.Thread(target=self.recv_worker)
        self.rx_thread.start()
        self.rx_queue = rx_queue

        print(f'Client connection opened on "{os.path.join(skt_dir, ident)}."')

    def __del__(self):
        self.active = False
        self.rx_thread.join()

        if os.path.exists(os.path.join(self.skt_dir, self.ident)):
            self.conn.close()
            os.remove(os.path.join(self.skt_dir, self.ident))
            print(f'Client connection closed on "{os.path.join(self.skt_dir, self.ident)}."')

    def is_active(self):
        return self.active

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

    def __send(self, data):
        json_data = json.dumps({"payload": data}, separators=(",", ":"), encoding="utf-8")
        return self.conn.send(json_data)

    def send_command(self, cmd):
        return self.__send({"cmd": cmd})

    def send_message(self, msg):
        return self.__send({"msg": msg})

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"Connection(id={self.ident}, active={self.is_active()}"


class Server:
    def __init__(self, skt_dir="~/.sockets"):
        signal.signal(signal.SIGINT, self.__sigint_handler)

        self.skt_dir = os.path.abspath(os.path.expanduser(skt_dir))
        print(f"Socket handle directory: {self.skt_dir}")
        if not os.path.exists(self.skt_dir):
            os.makedirs(self.skt_dir)

        self.srv_ident = "hndshk"
        self.hndshk_f = os.path.join(self.skt_dir, self.srv_ident)
        self.hndshk_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.hndshk_sock.settimeout(None)
        self.rx_conns = {}
        self.rx_queue = Queue()

        self.stop_thread = threading.Thread(target=self.__stop_worker)
        self.stop_thread.daemon = True
        self.hndshk_thread = threading.Thread(target=self.__hndshk_worker)
        self.hndshk_thread.daemon = True

        self.running = False

    def __sigint_handler(self, sig, frame):
        print("\nSIGINT caught. Exiting.")
        self.running = False

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.__stop()

    def __open_connection(self, ident):
        self.rx_conns[ident] = Connection(self.skt_dir, ident, self.rx_queue)

    def __close_connection(self, ident):
        self.rx_conns[ident].send_command("close_connection")
        self.rx_conns.pop(ident).__del__()

    def run(self):
        print("Server running. Press ENTER any time to exit.")
        self.hndshk_sock.bind(self.hndshk_f)
        self.hndshk_sock.listen()
        self.hndshk_thread.start()
        self.running = True
        self.stop_thread.start()

        # Main loop
        while self.running:
            self.__process_rx_queue()

    def __process_rx_queue(self):
        try:
            self.__process_rx_item()

            while not self.rx_queue.empty():
                self.__process_rx_item()
        except Empty:
            pass

    def __process_rx_item(self):
        try:
            data = self.rx_queue.get(True, 0.2)
        except Empty:
            raise Empty

        print("Received: ", data)

        ident = data.get("ident")
        msg = data.get("payload").get("msg")
        cmd = data.get("payload").get("cmd")

        if cmd is not None:
            print("Command: ", cmd)
            if cmd == "close_connection":
                self.__close_connection(ident)

        elif msg is not None:
            print("Message: ", msg)

    def __stop(self):
        self.running = False
        self.hndshk_sock.close()

        if os.path.exists(os.path.join(self.skt_dir, self.srv_ident)):
            os.remove(self.hndshk_f)

        idents = list(self.rx_conns.keys())
        for ident in idents:
            self.__close_connection(ident)

        self.rx_conns.clear()
        print("Done.")

    def __hndshk_worker(self):
        while True:
            print("Waiting for client connection...")
            hndshk_conn, _ = self.hndshk_sock.accept()
            print(f'Handshake connection opened on "{os.path.join(self.skt_dir, self.srv_ident)}".')

            ident = f"{random.randrange(2**24-1):06x}"
            self.__open_connection(ident)
            hndshk_conn.send(bytes(ident, "utf-8"))
            hndshk_conn.close()
            print(f'Handshake connection closed on "{os.path.join(self.skt_dir, self.srv_ident)}".')

    def __stop_worker(self):
        input()
        self.running = False

    def send(self, ident, data):
        return self.rx_conns[ident].send_message(data)
