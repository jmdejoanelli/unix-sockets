#!/usr/bin/env python3
import pyusock
import time

with pyusock.Client() as client:
    client.send_message("hello")

    for i in range(30):
        time.sleep(2)
        client.send_message(f"this is message number {i}")

    client.send_message("goodbyte")

