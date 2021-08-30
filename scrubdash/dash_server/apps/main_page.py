"""This module contains the layout and callbacks for the ScrubCam host page."""

import logging
from datetime import datetime

import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output

from scrubdash.dash_server.app import app
from scrubdash.dash_server.apps.navbar import default_navbar
from scrubdash.dash_server.networking import check_connection

log = logging.getLogger(__name__)

layout = dbc.Container(
    [
        default_navbar,
        dbc.Container(
            [
                html.Div(
                    html.H1(
                        'ScrubCam Devices',
                        className='header px-5 pt-3',
                    ),
                    className='text-center py-2'
                ),
                html.P(
                    ('This is the home page of ScrubDash. Click on a '
                        'device to get started!'),
                    className='gray-text text-center pb-4 mb-4 mt-1'
                ),
                html.Div(
                    id='host-grid'
                )
            ],
            style={
                'padding-bottom': '40px'
            }
        )
    ],
    style={'max-width': '1250px'},
    fluid=True
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
        message = dbc.Alert(
            'Waiting for a ScrubCam to connect...',
            className='text-center p-4',
            style={'font-size': '36px'},
            color='danger'
        )
        return message

    # Create the grid.  The grid only consists of one row since each
    # dbc.Card has a responsive width to the screen size.  Using only
    # one row is the only way to get a responsive row where there are
    # three columns (aka. dbc.Cards) per row for larger screens, two
    # cols per row for medium and small screens, and one col per row
    # for extra small screens.
    grid = []
    row = []

    # Sort the dictionary by hostname.
    host_timestamps = dict(sorted(host_timestamps.items(),
                                  key=lambda item: item[0]))
    for hostname, timestamp in host_timestamps.items():
        heartbeat = datetime.utcfromtimestamp(timestamp)
        connection_msg, text_color = check_connection(heartbeat)

        row.append(
            dbc.Col(
                dbc.Card(
                    [
                        # Link to a host's filter class grid page.
                        html.A(
                            html.H3(hostname),
                            href='/{}'.format(hostname),
                            className='text-center light-green'
                        ),
                        # The connected/disconnected message.
                        html.Div(
                            connection_msg,
                            className='text-center font-weight-bold',
                            style=text_color
                        )
                    ],
                    className='h-100',
                    style={'padding': '20px'},
                    outline=True,
                    color='success',
                ),
                className='pb-4 mt-1 mb-1',
                # Reponsive column widths for each screen size.
                xs=12, sm=6, md=6, lg=4, xl=4
            )
        )

    grid.append(dbc.Row(row))

    return grid
