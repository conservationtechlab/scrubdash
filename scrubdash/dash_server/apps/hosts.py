"""This module contains the layout and callbacks for the ScrubCam host page."""

import logging
from datetime import datetime

import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output

from scrubdash.dash_server.app import app
from scrubdash.dash_server.networking import check_connection

log = logging.getLogger(__name__)

layout = dbc.Container(
        [
            html.Div(
                id='host-grid'
            )
        ]
    )


@app.callback(Output('host-grid', 'children'),
              Input('host-timestamps', 'data'))
def update_cams(host_timestamps):
    """
    Update which ScrubCam hosts to show and update what their connection
    status is.

    This callback is triggered when the host timestamps dictionary changes.

    Parameters
    ----------
    host_timestamps : float
        The timestamp of the most recent heartbeat or message from the
        ScrubCam host

    Returns
    -------
    grid : Dash HTML Component
        A page layout written with Dash HTML Components that shows all the
        ScrubCam hosts that have connected to the current dashboard
        session and whether they are still connected or not.
    """
    if not host_timestamps:
        # No ScrubCam has connected yet.
        return "Waiting to connect to scrubcam..."

    # Create the grid.
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
                        # Link to a host's filter class grid page.
                        html.A(
                            html.Div(hostname),
                            href='/{}'.format(hostname)
                        ),
                        # The connected/disconnected message.
                        html.Div(
                            connection_msg,
                            style=text_color
                        )
                    ]
                )
            )
        )

        col += 1

        if col == 3:
            col = 0
            grid.append(dbc.Row(row))
            row = []

    # If we didn't have a multiple of 3 hosts, the last row never got
    # appended to grid, so we need to append it now.
    if col != 0:
        grid.append(dbc.Row(row))

    return grid
