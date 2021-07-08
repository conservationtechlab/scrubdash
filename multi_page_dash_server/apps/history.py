import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output
import base64
import pandas as pd
import csv
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO
import logging

from ..app import app

log = logging.getLogger(__name__)

layout = dbc.Container(
    html.Div(
        [
            html.H1(id='history-header'),
            dcc.Slider(
                id='confidence-slider',
                min=0,
                max=1,
                step=0.05,
                value=.6
            ),
            html.Div(id='slider-output-container'),
            dcc.Store(id='history-class'),
            dcc.Store(id='slider-val', data=.6),
            html.Div(id='test-output'),
            html.Div(id='history-grid'),
            dcc.Link(
                'Go back',
                href='/')
        ]
    )
)


# Updates the history-class when landing on the history page
# This triggers the rest of the history callbacks
@app.callback(Output('history-class', 'data'),
              Input('url', 'pathname'))
def display_history_page(pathname):
    return pathname


@app.callback(Output('history-header', 'children'),
              Input('history-class', 'data'),
              prevent_initial_call=True)
def create_history_header(pathname):
    # removes the '/' from the beginning of pathname
    animal = pathname[1:]
    header = '{} Images'.format(animal.capitalize())

    return header


@app.callback(Output('history-grid', 'children'),
              Input('confidence-slider', 'value'),
              Input('history-class', 'data'),
              prevent_initial_call=True)
def create_history_grid(selected_confidence, pathname):
    # creating the history grid
    df = pd.read_csv('image_log.csv')

    # removes the '/' from the beginning of pathname
    animal = pathname[1:]

    # resets the indices after dropping rows
    filtered = df[df['label'] == animal].reset_index(drop=True)
    # sorts paths in descending order (most recent to least recent)
    filtered.sort_values(ascending=False, by=['path'], inplace=True)
    # gets a list of animal images and lboxes
    image_list = filtered[['path', 'lboxes', 'datetime']].values.tolist()

    grid = []
    row = []
    col = 0

    # put 3 columns in a row
    # put 1 image per column
    for image in image_list:
        image_path = image[0]
        # base64_image = get_base64_image(image_path)

        source_img = Image.open(image_path).convert("RGB")
        # source_img = source_img.rotate(180)
        draw = ImageDraw.Draw(source_img)

        csv_path = image[1]
        with open(csv_path, newline='') as lboxes:
            reader = csv.reader(lboxes,
                                delimiter=',',
                                quotechar='"',
                                quoting=csv.QUOTE_MINIMAL)

            for lbox in reader:
                class_name = lbox[0]
                confidence = float(lbox[1])

                if confidence >= selected_confidence:
                    upper_left_x = int(lbox[2])
                    upper_left_y = int(lbox[3])
                    width = int(lbox[4])
                    height = int(lbox[5])

                    lower_right_x = upper_left_x + width
                    lower_right_y = upper_left_y + height

                    upper_left_corner = (upper_left_x, upper_left_y)
                    lower_right_corner = (lower_right_x, lower_right_y)

                    draw.rectangle([upper_left_corner,
                                    lower_right_corner])

                    font = ImageFont.truetype('Roboto/Roboto-Medium.ttf',
                                              48)

                    draw.text((upper_left_corner),
                              '{}, {}'.format(class_name, confidence),
                              font=font)

        source_img = source_img.resize((round(1920/8), round(1080/8)))

        buffer = BytesIO()
        source_img.save(buffer, format="JPEG")
        img_data = buffer.getvalue()

        base64_image = base64.b64encode(img_data).decode('ascii')

        row.append(
            dbc.Col(
                html.Div([
                    html.Img(
                        id=animal,
                        src='data:image/png;base64,{}'
                        .format(base64_image)
                    ),
                    html.Div(image[2])
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


@app.callback(Output('slider-output-container', 'children'),
              Input('confidence-slider', 'value'))
def slidervalue(value):
    return 'You have selected a confidence of: {}'.format(value)
