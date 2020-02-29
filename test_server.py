#!/usr/bin/env python3
import pyusock

with pyusock.Server() as srv:
    srv.run()
