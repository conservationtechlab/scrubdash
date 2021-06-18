#!/usr/bin/env python3

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import asyncio
import base64

from multiprocessing import Process, Queue


def start_asyncio(queue):
    import asyncio
    
    # reads in a message from a client and prints out the message received
    async def handle_echo(reader, writer):
        data = await reader.read(100)
        message = data.decode()
        print("{}".format(message))
        queue.put(message)

    # reference https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_server.py
    # creates a server that listens on localhost at port 8888 for incoming messages
    # all incoming messages are handled by handle_echo(reader, writer)
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
    

    app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
    app.layout = html.Div([
        html.Div("", id='content'),
        dcc.Interval(
            id='interval-component',
            interval=1.5*1000, # in milliseconds
            n_intervals=0
        )
    ])
    
    # updates content displayed on page
    @app.callback(Output('content', 'children'),
                 [Input('interval-component', 'n_intervals')], 
                 [State('content', 'children')], prevent_initial_call = True)
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