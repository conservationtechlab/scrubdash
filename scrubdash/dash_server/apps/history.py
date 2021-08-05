import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State, MATCH, ALL, ALLSMALLER
import base64
import pandas as pd
import csv
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO
import ast
import numpy as np
import logging

from scrubdash.dash_server.app import app

log = logging.getLogger(__name__)

layout = dbc.Container(
    html.Div(
        [
            html.H1(id='history-header'),
            html.Div(id='page-output-container'),
            dcc.Store(id='page-index', data=0),
            dcc.Store(id='image-csv'),
            dcc.Store(id='history-class'),
            dcc.Store(id='slider-val', data=.6),
            html.Div(id='test-output'),
            html.Div(
                id='history-grid',
                children=[
                    dbc.Row([
                        dbc.Col(
                            id={
                                'type': 'grid-square',
                                'index': j
                            },
                            children=dbc.Spinner(
                                children=html.Div([
                                    html.Img(
                                        id={
                                            'type': 'sq-img',
                                            'index': j
                                        },
                                        n_clicks=0),
                                    html.Div(
                                        id={
                                            'type': 'sq-header',
                                            'index': j
                                        })
                                ])
                            )
                        )
                        for j in range(i * 3, (i * 3) + 3)
                    ])
                    for i in range(3)
                ]),
            dbc.Modal(
                [
                    dbc.ModalHeader(id='modal-header'),
                    dbc.ModalBody(
                        id='modal-body',
                        children=[
                            html.Div(
                                [
                                    dcc.Slider(
                                        id='confidence-slider',
                                        min=0,
                                        max=1,
                                        step=0.05,
                                        value=.6
                                    ),
                                    html.Div(id='slider-output-container'),
                                ]),
                            html.Img(
                                id='modal-img')
                        ]),
                    dbc.ModalFooter(
                        dbc.Button(
                            'Close',
                            id='close',
                            className='ml-auto',
                            n_clicks=0)),
                ],
                id='modal',
                size='lg',
                is_open=False),
            dcc.Link(
                'Go back',
                href='/'),
            html.Div(
                id='pages',
                children=[
                    html.Button(
                        'Back',
                        id='prev-btn',
                        n_clicks=0,
                        style={'display': 'none'}),
                    html.Button(
                        'Next',
                        id='next-btn',
                        n_clicks=0,
                        style={'display': 'none'})
                ]
            )
        ]
    )
)


# Updates the history-class when landing on the history page
# This triggers the rest of the history callbacks
# This also retriggers on refresh
@app.callback(Output('history-class', 'data'),
              Output('image-csv', 'data'),
              Input('url', 'pathname'),
              State('log-path', 'data'))
def display_history_page(pathname, log_path):
    # removes the '/' from the beginning of pathname
    animal = pathname[1:]

    image_csv = pd.read_csv(log_path)

    # resets the indices after dropping rows
    filtered = image_csv[image_csv['labels'].str.contains(
        animal)].reset_index(drop=True)
    # sorts paths in descending order (most recent to least recent)
    filtered.sort_values(ascending=False, by=['path'], inplace=True)

    # converts the pandas dataframe to json to be stored in dcc.Store()
    json_result = filtered.to_json(orient='index')

    return pathname, json_result


# Updates the page header when landing on the history page
@app.callback(Output('history-header', 'children'),
              Input('history-class', 'data'),
              prevent_initial_call=True)
def create_history_header(pathname):
    # removes the '/' from the beginning of pathname
    animal = pathname[1:]
    header = '{} Images'.format(animal.capitalize())

    return header


# updates the grid images one by one
# the previous image must be updated before the next one starts
# allows user to see the images load
@app.callback(Output({'type': 'sq-img', 'index': MATCH}, 'src'),
              Output({'type': 'sq-header', 'index': MATCH}, 'children'),
              Output({'type': 'grid-square', 'index': MATCH}, 'style'),
              Input({'type': 'sq-img', 'index': MATCH}, 'children'),
              Input({'type': 'sq-img', 'index': ALLSMALLER}, 'src'),
              Input('history-class', 'data'),
              Input('page-index', 'data'),
              Input('image-csv', 'data'),
              prevent_initial_call=True)
def create_history_grid(prev_squares, index_handle, pathname, page, json_df):
    index = dash.callback_context.inputs_list[0]['id']['index']

    # converts image-csv from a json to a pandas dataframe
    filtered_csv = pd.read_json(json_df, orient='index')

    # gets a list of animal images and lboxes
    image_list = filtered_csv[['path', 'lboxes', 'datetime']].values.tolist()

    image_index = (page * 9) + index
    image_count = len(image_list)

    if image_index < image_count:
        # image index is in dataframe
        image = image_list[image_index]
        image_path = image[0]
        source_img = Image.open(image_path).convert("RGB")
        header = image[2]
        display = {'display': 'block'}
    else:
        # image index is not in dataframe (it's out of bounds)
        # return a white frame and hide the display
        white_frame = 255 * np.ones((1000, 1000, 3), np.uint8)
        source_img = Image.fromarray(white_frame)
        header = ""
        display = {'display': 'none'}

    # resize image to show in grid
    source_img = source_img.resize((round(1920 / 8), round(1080 / 8)))

    # create temporary buffer to get image binary
    buffer = BytesIO()
    source_img.save(buffer, format="JPEG")
    img_data = buffer.getvalue()
    base64_image = base64.b64encode(img_data).decode('ascii')

    return 'data:image/png;base64,{}'.format(base64_image), header, display


# shows user what the slider value is
@app.callback(Output('slider-output-container', 'children'),
              Input('confidence-slider', 'value'))
def slider_value(value):
    return 'You have selected a confidence of: {}'.format(value)


# updates page index on button click
@app.callback(Output('page-index', 'data'),
              Input('prev-btn', 'n_clicks'),
              Input('next-btn', 'n_clicks'),
              State('page-index', 'data'),
              prevent_initial_call=True)
def next_page(prev_btn, next_btn, page):
    ctx = dash.callback_context

    # gets the id of the component that triggered the callback
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'next-btn':
        page = page + 1
    else:
        page = page - 1

    return page


# determines which buttons to render
# the 'next' button is rendered if there are more images to show
# the 'back' button is rendered if there are previous images to show
@app.callback(Output('prev-btn', 'style'),
              Output('next-btn', 'style'),
              Input('page-index', 'data'),
              Input('image-csv', 'data'),
              prevent_initial_call=True)
def render_buttons(page, json_df):
    # converts image-csv from a json to a pandas dataframe
    image_csv = pd.read_json(json_df, orient='index')
    image_count = len(image_csv)

    # largest index of images currently shown
    current_max_image_index = (page + 1) * 9

    # checks to see if there are more images to show
    if image_count >= current_max_image_index:
        render_next = True
    else:
        render_next = False

    # checks if there are previous images to show
    if page > 0:
        render_prev = True
    else:
        render_prev = False

    if render_prev and render_next:
        render_results = {'display': 'block'}, {'display': 'block'}
    elif render_prev:
        render_results = {'display': 'block'}, {'display': 'none'}
    else:
        render_results = {'display': 'none'}, {'display': 'block'}

    return render_results


@app.callback(Output("modal", "is_open"),
              Output('modal-img', 'src'),
              Output('modal-header', 'children'),
              Input({'type': 'sq-img', 'index': ALL}, 'n_clicks'),
              Input('close', 'n_clicks'),
              Input('confidence-slider', 'value'),
              State({'type': 'sq-header', 'index': ALL}, 'children'),
              State('modal-header', 'children'),
              State("modal", "is_open"),
              State('image-csv', 'data'),
              prevent_initial_call=True)
def toggle_modal(img_clicks, close_btn, selected_confidence, img_headers,
                 modal_header, modal_open, json_df):
    # get the id of the component that triggered the callback
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]

    try:
        # trigger was clicking on an image (a sq-img component)
        square = ast.literal_eval(trigger)['index']
    except ValueError:
        # trigger was close button
        if trigger == 'close':
            # close the window, empty the img src, and empty the img header
            return False, '', ''

        if trigger == 'confidence-slider':
            # user clicked outside modal component to close
            # callback triggered by resetting slider value to 0.6 but modal
            # is_open is False
            if not modal_open:
                return False, '', ''

            # find square index of image
            np_img_headers = np.array(img_headers)
            square = int(np.where(np_img_headers == modal_header)[0][0])

    # get the timestamp of the clicked image
    timestamp = img_headers[square]

    image_csv = pd.read_json(json_df, orient='index')
    filtered_csv = image_csv[image_csv['datetime'] == timestamp]
    image_list = filtered_csv[['path', 'lboxes', 'datetime']].values.tolist()
    image = image_list[0]
    image_path = image[0]

    source_img = Image.open(image_path).convert("RGB")
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

                font_path = ('scrubdash/dash_server/assets/'
                             'Roboto/Roboto-Medium.ttf')
                font = ImageFont.truetype(font_path, 48)

                draw.text((upper_left_corner),
                          '{}, {}'.format(class_name, confidence),
                          font=font)

    source_img = source_img.resize((round(1920 / 2), round(1080 / 2)))

    # create temporary buffer to get image binary
    buffer = BytesIO()
    source_img.save(buffer, format="JPEG")
    img_data = buffer.getvalue()
    base64_image = base64.b64encode(img_data).decode('ascii')

    return True, 'data:image/png;base64,{}'.format(base64_image), image[2]


# resets slider value to 0.6 after closing the modal component
@app.callback(Output('confidence-slider', 'value'),
              Input('modal', 'is_open'),
              State('confidence-slider', 'value'),
              prevent_initial_call=True)
def reset_slider(modal, selected_confidence):
    # modal window is closed so reset slider value
    if not modal:
        return 0.6

    return selected_confidence