#!/usr/bin/env python3

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import asyncio
import base64
import struct
import pickle

"""
This program consists of 3 processes: 1. main 2. asyncio server 3. dash
server

The main process creates a shared Queue and uses multiprocessing to
spawn an asyncio processes and a dash processes. The shared Queue is
passed as a parameter to each process.

The asyncio server listens on port 8888 on localhost and puts any
messages it receives into the shared Queue. Every 1.5 seconds, the dash
server checks the Queue to see if anything was added to it. If so, it
removes each entry from the Queue and adds the image stored inside to
the website. The website ends up rendering the most recent image for
each animal class.

Additionally, clicking on an image will take you to a new page that
shows all the photos taken for that animal. The images are shown in
rows of 3, from most recent to least recent.

app_V2.py is best used with client.py from 6-21-2021. Pressing 'enter'
will send a new image to the asyncio server, which will be rendered by
dash.
"""





def start_dash(queue):
    import dash
    import dash_core_components as dcc
    import dash_bootstrap_components as dbc
    import dash_html_components as html
    from dash.dependencies import Input, Output, State
    import base64
    import pandas as pd



    app.layout = html.Div(
        [
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content')
        ]
    )

    # Update the index
    @app.callback(Output('page-content', 'children'),
                  Input('url', 'pathname'))
    def display_page(pathname):
        if pathname == '/':
            return index_page
        else:
            return create_history_page(pathname)

    
    app.run_server()



