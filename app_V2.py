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
receives into the shared Queue. Every 1.5 seconds, the dash server checks the
Queue to see if anything was added to it. If so, it removes each entry from the
Queue and adds the image stored inside to the website. The website ends up
rendering the most recent image for each animal class.

Additionally, clicking on an image will take you to a new page that shows all
the photos taken for that animal. The images are shown in rows of 3, from most
recent to least recent.

app_V2.py is best used with client.py from 6-21-2021. Pressing 'enter' will
send a new image to the asyncio server, which will be rendered by dash.
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

        return filepath

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
    import base64
    import pandas as pd

    app = dash.Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True)

    app.layout = html.Div(
        [
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content')
        ]
    )

    index_page = dbc.Container(
        [
            html.Div(
                [
                    html.Div(
                        id='grid-content'),
                    dcc.Store(id='image-dict'),
                    dcc.Interval(
                        id='interval-component',
                        interval=1.5 * 1000,  # in milliseconds
                        n_intervals=0
                    )
                ],
                id='page-content')
        ]
    )

    # function to update image dictionary
    # will end up needing to include a parameter that lists all the animals the
    # scrubcam is tracking
    def create_image_dict():
        # create uninitialized dictionary
        image_dict = {
            'cheetah': None,
            'condor': None,
            'elephant': None,
            'flamingo': None,
            'hippo': None,
            'koala': None,
            'lion': None,
            'panda': None,
            'penguin': None,
            'polar-bear': None,
            'rhino': None,
            'tortoise': None}

        # initialize image path to most recent entry in image_log.csv
        df = pd.read_csv('image_log.csv')

        for key in image_dict:
            # resets the indices after dropping rows
            filtered = df[df['label'] == key].reset_index(drop=True)
            # sorts paths in descending order (most recent to least recent)
            filtered.sort_values(ascending=False, by=['path'], inplace=True)

            # at least one image exists for this animal
            if len(filtered.index) > 0:
                # get most recent image (the first row since sorted by desc
                # order)
                image_dict[key] = filtered.iloc[0].values[0]

        return image_dict

    # checks shared queue every 2 seconds to update image dictionary
    @app.callback(Output('image-dict', 'data'),
                  Input('interval-component', 'n_intervals'),
                  State('image-dict', 'data'))
    def update_image_dict(n_intervals, image_dict):
        if image_dict is None:
            image_dict = create_image_dict()

        while not queue.empty():
            image = queue.get(block=False)
            filename = image['img_path']
            class_name = image['label']
            image_dict[class_name] = filename

        return image_dict

    # returns base64 encoding of image
    def get_base64_image(filename):
        base64_image = None
        if filename is None:
            return ""

        with open(filename, 'rb') as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('ascii')

        return base64_image

    # updates grid images when image dictionary changes
    @app.callback(Output('grid-content', 'children'),
                  Input('image-dict', 'data'))
    def update_grid(image_dict):
        grid = []
        row = []
        col = 0

        # put 3 columns in a row
        # put 1 image per column
        for class_name, filename in image_dict.items():
            base64_image = get_base64_image(filename)
            row.append(
                dbc.Col(
                    html.Div(
                        html.A(
                            html.Img(
                                id=class_name,
                                src='data:image/png;base64,{}'.format(base64_image)),
                            href='/{}'.format(class_name)))))
            col += 1

            if col == 3:
                col = 0
                # need to copy since I'm reusing the row variable and python
                # stores values in a dict as a pointer. To avoid overwriting
                # data, I make a copy.
                grid.append(dbc.Row(row.copy()))
                row = []

        # if we didn't have a multiple of 3 images, the last row never got
        # appended to grid
        if col != 0:
            grid.append(dbc.Row(row.copy()))

        return grid

    # creates grid of all images for the animal
    def create_history_page(pathname):
        # removes the '/' from the beginning of pathname
        animal = pathname[1:]
        h1_header = '{} Images'.format(animal.capitalize())

        # creating the history grid
        df = pd.read_csv('image_log.csv')

        # resets the indices after dropping rows
        filtered = df[df['label'] == animal].reset_index(drop=True)
        # sorts paths in descending order (most recent to least recent)
        filtered.sort_values(ascending=False, by=['path'], inplace=True)
        # gets a list of animal images
        image_list = filtered['path'].to_list()

        grid = []
        row = []
        col = 0

        # put 3 columns in a row
        # put 1 image per column
        for image in image_list:
            base64_image = get_base64_image(image)
            row.append(
                dbc.Col(
                    html.Div(
                        html.Img(
                            id=animal,
                            src='data:image/png;base64,{}'.format(base64_image)))))
            col += 1

            if col == 3:
                col = 0
                # need to copy since I'm reusing the row variable and python
                # stores values in a dict as a pointer. To avoid overwriting
                # data, I make a copy.
                grid.append(dbc.Row(row.copy()))
                row = []

        # if we didn't have a multiple of 3 images, the last row never got
        # appended to grid
        if col != 0:
            grid.append(dbc.Row(row.copy()))

        history_page_layout = dbc.Container(
            html.Div(
                [
                    html.H1(h1_header),
                    html.Div(grid),
                    dcc.Link(
                        'Go back',
                        href='/')
                ]
            )
        )

        return history_page_layout

    # Update the index
    @app.callback(Output('page-content', 'children'),
                  [Input('url', 'pathname')])
    def display_page(pathname):
        if pathname == '/':
            return index_page
        else:
            return create_history_page(pathname)

    app.run_server()


if __name__ == '__main__':
    q = Queue()
    asyncio = Process(target=start_asyncio, args=(q,))
    dash = Process(target=start_dash, args=(q,))
    asyncio.start()
    dash.start()
