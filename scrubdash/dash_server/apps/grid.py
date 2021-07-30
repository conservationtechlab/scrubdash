import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output
from PIL import Image
from io import BytesIO
import base64
import numpy as np
import logging

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
    # change nothing if image dictionary is empty
    if not image_dict:
        return "Waiting to connect to scrubcam..."

    grid = []
    row = []
    col = 0

    # put 3 columns in a row
    # put 1 image per column
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
            # need to copy since I'm reusing the row variable and
            # python stores values in a dict as a pointer. To avoid
            # overwriting data, I make a copy.
            grid.append(dbc.Row(row.copy()))
            row = []

    # if we didn't have a multiple of 3 images, the last row never
    # got appended to grid
    if col != 0:
        grid.append(dbc.Row(row.copy()))

    return grid
