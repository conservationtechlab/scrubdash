#!/usr/bin/env python3

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import asyncio
import base64
from multiprocessing import Process, Queue
import struct
import pickle

"""
This program consists of 3 processes: 1. main 2. asyncio server 3. dash server

The main process creates a shared Queue and uses multiprocessing to spawn an
asyncio processes and a dash processes. The shared Queue is passed as a
parameter to each process.

The asyncio server listens on port 8888 on localhost and puts any messages it
receives into the shared Queue. Every 2 seconds, the dash server will check the
Queue to see if anything was added to it. If so, it gets each element and adds
it to the website. The website ends up rendering all the text that was received
by the asyncio server.

app_V2.py is best used with client.py from 6-18-2021. One can also send
messages to the asyncio terminal by executing `nc localhost 8888` in another
terminal and typing in a message.
"""


def start_asyncio(queue):
    import os
    import json
    import asyncio
    from datetime import datetime

    RECORD_FOLDER = 'saved_images/'

    def save_image_to_disk(image, class_name):
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%dT%Hh%Mm%Ss.%f')[:-3]
        filename = '{}_{}.jpeg'.format(timestamp, class_name)
        filepath = os.path.join(RECORD_FOLDER, filename)

        # saving image to disk
        with open(filepath, 'wb') as saved_img:
            saved_img.write(image)

        # update csv log that stores all image records
        with open('image_log.csv', 'a') as image_csv:
            image_csv.write('{},{}\n'.format(filepath, class_name))

        return filename

    # reads in two messages from client and prints out the messages received

    async def handle_echo(reader, writer):
        # read size of image bytestream
        image_struct = await reader.read(struct.calcsize('<L'))
        image_size = struct.unpack('<L', image_struct)[0]
        # for debugging: print(imae_size)

        # read in image bytestream
        image = await reader.readexactly(image_size)

        # read size of lboxes struct
        lboxes_struct = await reader.read(struct.calcsize('<L'))
        lboxes_size = struct.unpack('<L', lboxes_struct)[0]

        # read in lboxes bytestream
        lboxes_struct = await reader.readexactly(lboxes_size)
        lboxes = pickle.loads(lboxes_struct)
        # for debugging: print(lboxes)  # ex: [{'class_name': 'cheetah'}]
        class_name = lboxes[0]['class_name']

        # save image to disk and to the csv
        filename = save_image_to_disk(image, class_name)

        # send image path and class name to dash server
        message = {"img_path": filename, "label": class_name}
        queue.put(message)

    # reference:
    # https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_server.py
    # creates a server that listens on localhost at port 8888 for incoming
    # messages all incoming messages are handled by handle_echo(reader, writer)

    async def run_forever():
        server = await asyncio.start_server(handle_echo, '127.0.0.1', 8888)

        async with server:
            # the server will listen forever until we close it
            await server.serve_forever()

        server.close()

    asyncio.run(run_forever())


def start_dash(queue):
    import dash
    import dash_core_components as dcc
    import dash_bootstrap_components as dbc
    import dash_html_components as html
    from dash.dependencies import Input, Output, State

    app = dash.Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True)
    app.layout = html.Div([
        html.Div("", id='content'),
        dcc.Interval(
            id='interval-component',
            interval=1.5 * 1000,  # in milliseconds
            n_intervals=0
        )
    ])

    # updates content displayed on page
    @app.callback(Output('content', 'children'),
                  [Input('interval-component', 'n_intervals')],
                  [State('content', 'children')], prevent_initial_call=True)
    def empty_queue(n_intervals, content):
        # prints everything in the Queue
        while not queue.empty():
            content += ", {}".format(queue.get(block=False))
        print("content: {}".format(content))
        return(content)

    app.run_server()


if __name__ == '__main__':
    q = Queue()
    asyncio = Process(target=start_asyncio, args=(q,))
    dash = Process(target=start_dash, args=(q,))
    asyncio.start()
    dash.start()
