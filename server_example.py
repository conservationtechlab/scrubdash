#!/usr/bin/env python3

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import os
import logging
import asyncio
from threading import Thread

"""
This program simulates how I would create a monolithic program.
The intent is that the dash server runs on the main thread, with the asyncio server that receives socket connections being run on a different thread.

The problem described in previous commits and versions of this program have been resolved. It turns out that having the argument debug=True in app.run_server() spawns a new Python interpreter to reload the page when code changes. Taking out this argument fixes this problem. The debug argument is primarily used for development and reloads the page when code changes. Omitting this argument still allows the page to reload when a callback changes an html element's tag so removing this argument is not harmful at all.

A callback is executed every two seconds to update the interval counter on the page. This shows that dash is still running and updating, even when another thread is running an asyncio server.

Running the command `nc localhost 8888` and typing in a message in another terminal will send a message to the asyncio server and you should see the message printed out in the terminal running server_example.py. You can also run client.py instead of `nc localhost 8888` to test this program. This shows that this program is able to run both the asyncio and the dash server concurrently.
"""

# *** Server Code (can ignore) ***

# reads in a message from a client and prints out the message received
async def handle_echo(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    print("{}".format(message))

# reference https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_server.py
# creates a server that listens on localhost at port 8888 for incoming messages
# all incoming messages are handled by handle_echo(reader, writer)
async def run_forever():
    server = await asyncio.start_server(handle_echo, '127.0.0.1', 8888)

    async with server:
        # the server will listen forever until we close it
        await server.serve_forever()

    server.close()

# *** End of Server Code ***

# *** Function to start server ***
def server_run():
    asyncio.run(run_forever())


# *** Start of Dash Part ***

app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.layout = html.Div([
    html.Div(html.P("interval: 0"), id='content'),
    dcc.Interval(
        id='interval-component',
        interval=1.5*1000, # in milliseconds
        n_intervals=0
    )
])

# change interval counter displayed on page
@app.callback(Output('content', 'children'),
              Input('interval-component', 'n_intervals'), prevent_initial_call = True)
def change_interval(n_intervals):
    return(html.P("interval: {}".format(str(n_intervals))))

# *** End of Dash Part ***

if __name__ == '__main__':
    try: 
        # run async stuff in another thread
        # create one thread that starts the server
        th1 = Thread(target=server_run)

        # start the server thread
        th1.start()

        # run our dash website server
        app.run_server()

        th1.join()

    except KeyboardInterrupt:
        # used for previous debugging purposes. can ignore
        logging.info("Main (pid: {})  : all done".format(os.getpid()))
