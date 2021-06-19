#!/usr/bin/env python3

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output
import base64
import pandas as pd
import asyncio
from threading import Thread

"""
This program mimics a client that is supposed to send images to the server.

I simulate this by having asyncio run update_img_src(), which reads hardcoded
image paths from a csv and updates a file variable. To ensure that this path
will work with dash, I also run a dash server that updates the image source to
the path contained in the file variable. Since the file variable is changing
every 2 seconds from update_img_src(), dash should be rerendering the image
every 2 seconds as well (dash rerenders every 2 seconds since I set the
dcc.Interval component to update n_intervals every 2 seconds).
"""

# ** global variables **
df = pd.read_csv('client.csv')
filename = 'client_imgs/elephant-1.jpg'
file = None
with open(filename, 'rb') as image_file:
    file = base64.b64encode(image_file.read()).decode('ascii')

# ** Async Part ** reference:
# https://stackoverflow.com/questions/67206119/asyncio-run-dash-flask-server-with-another-coroutine-concurrently


async def update_img_src(stop):
    i = 0
    parity = 0      # 0 parity is even, 1 parity is odd
    while not stop:
        parity = 0 if parity else 1
        for i in range(12):
            row = (((i) * 2) + 1) % 24 if parity else ((i) * 2) % 24
            print(i, row, parity)
            global filename
            filename = df.iloc[row].values[0]
            with open(filename, 'rb') as image_file:
                global file
                file = base64.b64encode(image_file.read()).decode('ascii')
            await asyncio.sleep(1.5)


def async_main_wrapper(stop):
    # Not async Wrapper around update_img_src to run it as target function of
    # Thread
    asyncio.run(update_img_src(stop))

# *** Dash Part ***


app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True)
app.layout = html.Div([
    html.Img(id='img', src='data:image/png;base64,{}'.format(file)),
    dcc.Interval(
        id='interval-component',
        interval=1.5 * 1000,  # in milliseconds
        n_intervals=0
    )
])

# change image callback


@app.callback(Output('img', 'src'),
              Input('interval-component', 'n_intervals'))
def change_img(n_clicks):
    # print(filename)
    return('data:image/png;base64,{}'.format(file))


if __name__ == '__main__':
    # run async stuff in another thread
    stop = False
    th1 = Thread(target=async_main_wrapper, args=(stop,))
    th1.start()

    try:
        # run Dash server
        app.run_server()

    except KeyboardInterrupt:
        stop = True
        th1.join()
