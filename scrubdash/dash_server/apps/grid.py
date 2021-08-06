import logging
import base64
from io import BytesIO

import numpy as np
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output
from PIL import Image

from scrubdash.dash_server.app import app

log = logging.getLogger(__name__)

layout = dbc.Container(
        [
            html.Div(
                [
                    html.Div(
                        html.A("Graphs", href='/graphs')
                    ),
                    html.Div(
                        "Waiting to connect to scrubcam...",
                        id='grid-content'),
                ],
                id='index-content'
            )
        ]
    )


# updates grid images when image dictionary changes
@app.callback(Output('grid-content', 'children'),
              Input('image-dict', 'data'))
def update_grid(image_dict):
    """
    Updates grid images when the image dictionary changes

    Parameters
    ----------
    image_dict : dict of { 'class_name' : str }
        The dictionary that maps the most recent image for each
        class_name. The image is represented as the absolute path
        to the image

    Returns
    -------
    Dash HTML Component
        The grid page layout written with Dash HTML Components. It
        shows the most recent images received for each class in filter
        classes
    """
    # change nothing if image dictionary is empty
    if not image_dict:
        return "Waiting to connect to scrubcam..."

    grid = []
    row = []
    col = 0

    # put 3 columns in a row with 1 image per column
    # image base64 reference: https://stackoverflow.com/questions/
    # 3715493/encoding-an-image-file-with-base64
    for class_name, filename in image_dict.items():
        if not filename:
            # white rectangle if no image for class
            white_frame = 255 * np.ones((1000, 1000, 3), np.uint8)
            source_img = Image.fromarray(white_frame)
        else:
            source_img = Image.open(filename).convert("RGB")

        source_img = source_img.resize((round(1920/8), round(1080/8)))

        buffer = BytesIO()
        source_img.save(buffer, format="JPEG")
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
                                .format(base64_image)),
                            href='/{}'.format(class_name)
                        ),
                        html.Div(class_name.capitalize())
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
