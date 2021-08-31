"""
This module contains the layout and callbacks for a ScrubCam's labels page.
"""

import base64
import logging
from io import BytesIO

import dash
import dash_bootstrap_components as dbc
import dash_html_components as html
import numpy as np
from dash.dependencies import Input, Output
from PIL import Image

from scrubdash.dash_server.app import app
from scrubdash.dash_server.apps.navbar import full_navbar

log = logging.getLogger(__name__)

layout = dbc.Container(
    [
        full_navbar,
        # Where the grid renders.
        dbc.Container(
            [
                html.Div(
                    html.H1(
                        '',
                        id='labels-header',
                        className='header px-5 pt-3',
                    ),
                    className='text-center py-2'
                ),
                html.P(
                    '',
                    id='labels-desc',
                    className='gray-text text-center pb-4 mb-4 mt-1'
                ),
                html.Div(
                    id='labels-grid'
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


@app.callback(Output('labels-header', 'children'),
              Output('labels-desc', 'children'),
              Input('url', 'pathname'))
def update_labels_header(pathname):
    """
    Update the labels page header on page load or refresh.

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location

    Returns
    -------
    header : str
        The header for the labels page that includes the hostname
    desc: str
        A description of what the labels page shows
    """
    # Parse hostname.
    hostname = pathname.split('/')[1]
    header = hostname + ' Labels'

    desc = ('This page shows the labels the {} device takes images of. Each '
            'image in the grid shows the most recent photo taken for that '
            'label. Click on the image to view that label\'s history page or '
            'click on the graphs link in the navbar to visualize image data.'
            .format(hostname))

    return header, desc


@app.callback(Output('labels-grid', 'children'),
              Input('host-images', 'data'),
              Input('url', 'pathname'))
def update_grid(host_images, pathname):
    """
    Update the grid to show the most recent images taken for each class.
    This callback is triggered when the host image dictionary changes.

    Parameters
    ----------
    host_images : dict of { 'hostname': str }
        A dictionary that contains the absolute path to each
        host's session image log
    pathmame : str
        The pathname of the url in window.location

    Returns
    -------
    Dash HTML Component
        The grid page layout written with Dash HTML Components. It
        shows the most recent images received for each class in filter
        classes

    Notes
    -----
    Reference for base64 encoding the image: https://stackoverflow.com/questions/3715493/encoding-an-image-file-with-base64
    """
    # No ScrubCam has connected yet.  This is a rare edge case where the
    # ScrubCam has not connected yet but someone loaded the page by
    # manually typing the url.
    if not host_images:
        return 'Waiting to connect to scrubcam...'

    # Parse hostname.
    hostname = pathname.split('/')[1]
    # Get hostname's image dictionary.
    try:
        image_dict = host_images[hostname]
    except KeyError:
        # KeyError when returning to the home page since the hostname
        # is ''.
        return dash.no_update

    # Create the grid.  The grid only consists of one row since each
    # dbc.Card has a responsive width to the screen size.  Using only
    # one row is the only way to get a responsive row where there are
    # three columns (aka. dbc.Cards) per row for larger screens, two
    # cols per row for medium and small screens, and one col per row
    # for extra small screens.
    grid = []
    row = []

    image_dict = host_images[hostname]
    # Sort the dictionary by class_name.
    image_dict = dict(sorted(image_dict.items(), key=lambda item: item[0]))
    for class_name, filename in image_dict.items():
        if not filename:
            # Draw a white rectangle if no image found for class.
            white_frame = 255 * np.ones((1000, 1000, 3), np.uint8)
            source_img = Image.fromarray(white_frame)
        else:
            source_img = Image.open(filename).convert('RGB')

        # Reduce the image size so it renders faster and fits on the page.
        source_img = source_img.resize((round(1920 / 4), round(1080 / 4)))

        # Create a temporary buffer to get image binary.
        buffer = BytesIO()
        source_img.save(buffer, format='JPEG')
        # Get the bytes of the resized image.
        img_data = buffer.getvalue()
        base64_image = base64.b64encode(img_data).decode('ascii')

        row.append(
            dbc.Col(
                html.Div(
                    [
                        html.A(
                            html.Img(
                                id=class_name,
                                src='data:image/png;base64,{}'
                                .format(base64_image),
                                className='rounded'
                            ),
                            href='/{}/{}'.format(hostname, class_name)
                        ),
                        html.H4(
                            html.A(
                                class_name.capitalize(),
                                href='/{}/{}'.format(hostname, class_name),
                                className='light-green'
                            ),
                            className='pt-3',
                        )
                    ],
                    className='text-center'
                ),
                className='pb-4 mt-1 mb-1',
                # Reponsive column widths for each screen size.
                xs=12, sm=6, md=6, lg=4, xl=4
            )
        )

    grid.append(dbc.Row(row))

    return grid
