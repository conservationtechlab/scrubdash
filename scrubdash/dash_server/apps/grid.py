"""
This module contains the layout and callbacks for a ScrubCam's image class
page.
"""

import base64
import logging
from io import BytesIO

import dash_bootstrap_components as dbc
import dash_html_components as html
import numpy as np
from dash.dependencies import Input, Output
from PIL import Image

from scrubdash.dash_server.app import app

log = logging.getLogger(__name__)

layout = dbc.Container(
        [
            html.Div(
                [
                    # Link to the host's graphs page.
                    html.Div(
                        html.A("Graphs", href='', id='graph-link')
                    ),
                    # Where the grid renders.
                    html.Div(
                        id='grid-content'),
                    # Back button to the ScrubCam hosts page.
                    html.A(
                        id='grid-back-btn',
                        children='Go back to ScrubCam hosts page',
                        href='/')
                ]
            )
        ]
    )


@app.callback(Output('graph-link', 'href'),
              Input('url', 'pathname'))
def update_graph_link(pathname):
    """
    Update the graphs page link to be host specific.

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location

    Returns
    -------
    href: HTML Anchor href attribute
        The href to the host's graphs page
    """
    # Parse hostname.
    hostname = pathname.split('/')[1]

    # Create href.
    href = '{}/graphs'.format(hostname)

    return href


@app.callback(Output('grid-content', 'children'),
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
    image_dict = host_images[hostname]

    # Create the grid.
    grid = []
    row = []
    col = 0

    image_dict = host_images[hostname]
    # Put 3 columns in a row with 1 image per column.
    for class_name, filename in image_dict.items():
        if not filename:
            # Draw a white rectangle if no image found for class.
            white_frame = 255 * np.ones((1000, 1000, 3), np.uint8)
            source_img = Image.fromarray(white_frame)
        else:
            source_img = Image.open(filename).convert('RGB')

        # Reduce the image size so it renders faster.
        source_img = source_img.resize((round(1920/8), round(1080/8)))

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
                                .format(base64_image)
                            ),
                            href='/{}/{}'.format(hostname, class_name)
                        ),
                        html.Div(class_name.capitalize())
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
