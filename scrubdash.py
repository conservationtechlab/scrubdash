#!/usr/bin/env python3

from multiprocessing import Process, Queue
from asyncio_server import asyncio_server
from dash_server import start_dash

if __name__ == '__main__':
    q = Queue()
    asyncio_server = asyncio_server(q)
    asyncio = Process(target=asyncio_server.start_server)
    dash = Process(target=start_dash, args=(q,))
    asyncio.start()
    dash.start()
