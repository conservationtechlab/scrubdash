import logging
from datetime import datetime

import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output

from scrubdash.dash_server.app import app
from scrubdash.dash_server.utils import check_connection

log = logging.getLogger(__name__)

layout = dbc.Container(
        [
            html.Div(
                id='cam-content'
            )
        ]
    )


# TODO: change docstring to reflect changed parameters to host dicts
# updates cam links when cam image dictionary changes
@app.callback(Output('cam-content', 'children'),
              Input('host-timestamps', 'data'))
def update_cams(host_timestamps):
    # change nothing if image dictionary is empty
    if not host_timestamps:
        return "Waiting to connect to scrubcam..."

    grid = []
    row = []
    col = 0

    for hostname, timestamp in host_timestamps.items():
        heartbeat = datetime.utcfromtimestamp(timestamp)
        connection_msg, text_color = check_connection(heartbeat)

        row.append(
            dbc.Col(
                html.Div(
                    [
                        html.A(
                            html.Div(hostname),
                            href='/{}'.format(hostname)
                        ),
                        html.Div(
                            connection_msg,
                            style=text_color
                        )
                    ])))
        col += 1

        if col == 3:
            col = 0
            grid.append(dbc.Row(row))
            row = []

    # if we didn't have a multiple of 3 images, the last row never
    # got appended to grid. So we need to append it now
    if col != 0:
        grid.append(dbc.Row(row))

    return grid
