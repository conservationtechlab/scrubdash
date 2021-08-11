import ast
import csv
import base64
import logging
from io import BytesIO

import dash
import dash_daq as daq
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import pandas as pd
import numpy as np
from dash.dependencies import Input, Output, State, MATCH, ALL, ALLSMALLER
from PIL import Image, ImageFont, ImageDraw

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
                                    dcc.RangeSlider(
                                        id='confidence-slider',
                                        min=0,
                                        max=1,
                                        step=0.05,
                                        value=[0, .6]
                                    ),
                                    html.Div(id='slider-output-container'),
                                ]),
                            html.Img(
                                id='modal-img'
                            ),
                            dbc.Button(
                                "Pick font color",
                                color='primary',
                                id='collapse-button',
                                n_clicks=0
                            ),
                            dbc.Collapse(
                                daq.ColorPicker(
                                    id='color-picker',
                                    label=('Color Picker'
                                           '(alpha value not supported)'),
                                    value=dict(rgb=dict(r=0, g=0, b=0))
                                ),
                                id='collapse-body',
                                is_open=False
                            )
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
    """
    Initializes the history page by updating the history class and
    image log json dataframe when loading the page and on refresh

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location
    log_path : str
        The absolute path of the image log for the current user session

    Returns
    -------
    str
        The pathname of the url in window.location
    json
        A json representation of the transformed dataframe used by the
        histogram and time graph
    """
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
    """
    Updates the page header when loading the history page

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location

    Returns
    -------
    str
        The page header indicating what class the history page is for
    """
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
def create_history_grid(index_handle, prev_squares, pathname, page, json_df):
    """
    Updates each image one by one in the 3x3 grid when the page index,
    image log path, or history class changes.

    Parameters
    ----------
    index_handle : str
        The image header (the image timestamp)
    prev_squares : list of str
        A list of base64 encoded images sources whose index is smaller
        than the current image
    pathname : str
        The pathname of the url in window.location
    page : int
        The current 3x3 grid page. Pages are indexed at 0
    json_df
        A json representation of the transformed dataframe used by the
        histogram and time graph

    Returns
    -------
    str
        The souce of the base64 encode dimage
    str
        The image header (the image timestamp)
    CSS Display Property
        A CSS display property specifying whether to hide or show the
        grid square
    """
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
        source_img = Image.open(image_path).convert('RGB')
        header = image[2]
        display = {'display': 'block'}
    else:
        # image index is not in dataframe (it's out of bounds)
        # return a white frame and hide the display
        white_frame = 255 * np.ones((1000, 1000, 3), np.uint8)
        source_img = Image.fromarray(white_frame)
        header = ''
        display = {'display': 'none'}

    # resize image to show in grid
    source_img = source_img.resize((round(1920 / 8), round(1080 / 8)))

    # create temporary buffer to get image binary
    buffer = BytesIO()
    source_img.save(buffer, format='JPEG')
    img_data = buffer.getvalue()
    base64_image = base64.b64encode(img_data).decode('ascii')

    return 'data:image/jpeg;base64,{}'.format(base64_image), header, display


# shows user what the slider value is
@app.callback(Output('slider-output-container', 'children'),
              Input('confidence-slider', 'value'))
def slider_value(values):
    """
    Shows the slider value in the modal window

    Parameters
    ----------
    values : list of float
        The selected minimum and maximum values of the confidence slider

    Returns
    -------
    str
        A message displaying the selected confidence
    """
    return 'You have selected a confidence interval of: {}'.format(values)


# updates page index on button click
@app.callback(Output('page-index', 'data'),
              Input('prev-btn', 'n_clicks'),
              Input('next-btn', 'n_clicks'),
              State('page-index', 'data'),
              prevent_initial_call=True)
def next_page(prev_btn, next_btn, page):
    """
    Updates the page index when clicking the `Next` or `Back` buttons

    Parameters
    ----------
    prev_btn : int
        The number of times the button has been clicked on
    next_btn : int
        The number of times the button has been clicked on
    page : int
        The current 3x3 grid page. Pages are indexed at 0

    Returns
    -------
    int
        The updated page number after clicking on the `Next` or `Back`
        buttons
    """
    ctx = dash.callback_context

    # gets the id of the component that triggered the callback
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'next-btn':
        page += 1
    else:
        page -= 1

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
    """
    Determines whether there are enough previous or following images to
    render the `Next` and `Back` buttons

    Parameters
    ---------
    page : int
        The current 3x3 grid page. Pages are indexed at 0
    json_df
        A json representation of the transformed dataframe used by the
        histogram and time graph

    Returns
    -------
    CSS Display Property
        A CSS display property specifying whether to render the `Back`
        button
    CSS Display Property
        A CSS display property specifying whether to render the `Next`
        button
    """
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
        render_results = ({'display': 'block'}, {'display': 'block'})
    elif render_prev:
        render_results = ({'display': 'block'}, {'display': 'none'})
    elif render_next:
        render_results = ({'display': 'none'}, {'display': 'block'})
    else:
        render_results = ({'display': 'none'}, {'display': 'none'})

    return render_results[0], render_results[1]


@app.callback(Output('modal', 'is_open'),
              Output('modal-img', 'src'),
              Output('modal-header', 'children'),
              Input({'type': 'sq-img', 'index': ALL}, 'n_clicks'),
              Input('close', 'n_clicks'),
              Input('confidence-slider', 'value'),
              Input('color-picker', 'value'),
              State({'type': 'sq-header', 'index': ALL}, 'children'),
              State('modal-header', 'children'),
              State('modal', 'is_open'),
              State('image-csv', 'data'),
              prevent_initial_call=True)
def toggle_modal(img_clicks, close_btn, selected_confidence, font_color,
                 img_headers, modal_header, modal_open, json_df):
    """
    Opens a modal component when an image in the history grid is
    clicked on

    Parameters
    ----------
    img_clicks : list of int
        A list of the number of clicks each image square in the grid
        has been clicked on
    close_btn : int
        The number of times the button has been clicked on
    selected_confidence : list of float
        The selected minimum and maximum values of the confidence
        slider
    font_color : dict of { 'hex': str,
                               'rgb': dict of { 'rgb' : 'r': int,
                                                        'g': int,
                                                        'b': int,
                                                        'a': int
                                              }
                             }
        The hex and rgb value of the selected font color
    img_headers : list of str
        A list of the timestamps for each image rendered in the history
        grid
    modal_header : str
        The header of the modal component. This is the timestamped of
        the image rendered in the modal component
    modal_open : bool
        A boolean that describes if the modal component is open or not
    json_df
        A json representation of the transformed dataframe used by the
        histogram and time graph

    Returns
    -------
    bool
        A boolean that describes if the modal component is open or not
    str
        A base64 encoded image source for the image that should be
        rendered in the modal component.
    str
        The header of the modal component. This is the timestamped of
        the image rendered in the modal component
    """
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
            # user clicked outside modal component to close this
            # callback triggered by resetting the slider value to 0.6
            # in the reset_slider callback but modal is_open is False
            if not modal_open:
                return False, '', ''

            # find square index of image
            np_img_headers = np.array(img_headers)
            square = int(np.where(np_img_headers == modal_header)[0][0])

        if trigger == 'color-picker':
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

    # open image as bytes
    source_img = Image.open(image_path).convert('RGB')
    draw = ImageDraw.Draw(source_img)

    # get csv containing lboxes
    csv_path = image[1]

    # get confidence min and max from range slider
    confidence_min = selected_confidence[0]
    confidence_max = selected_confidence[1]

    # get rgb from color picker
    rgb = font_color['rgb']
    font_color = (rgb['r'], rgb['g'], rgb['b'])

    # draw lboxes onto image
    with open(csv_path, newline='') as lboxes:
        reader = csv.reader(lboxes,
                            delimiter=',',
                            quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)

        for lbox in reader:
            class_name = lbox[0]
            confidence = float(lbox[1])

            if confidence >= confidence_min and confidence <= confidence_max:
                upper_left_x = int(lbox[2])
                upper_left_y = int(lbox[3])
                width = int(lbox[4])
                height = int(lbox[5])

                lower_right_x = upper_left_x + width
                lower_right_y = upper_left_y + height

                upper_left_corner = (upper_left_x, upper_left_y)
                lower_right_corner = (lower_right_x, lower_right_y)

                draw.rectangle([upper_left_corner,
                                lower_right_corner],
                               outline=font_color)

                font_path = ('scrubdash/dash_server/assets/'
                             'Roboto/Roboto-Medium.ttf')
                font = ImageFont.truetype(font_path, 48)

                draw.text((upper_left_corner),
                          '{}, {}'.format(class_name, confidence),
                          fill=font_color,
                          font=font)

    # resize image to show in modal component
    source_img = source_img.resize((round(1920 / 2), round(1080 / 2)))

    # create temporary buffer to get image binary
    buffer = BytesIO()
    source_img.save(buffer, format='JPEG')
    img_data = buffer.getvalue()
    base64_image = base64.b64encode(img_data).decode('ascii')

    return True, 'data:image/jpeg;base64,{}'.format(base64_image), image[2]


# resets slider value to 0.6 after closing the modal component
@app.callback(Output('confidence-slider', 'value'),
              Input('modal', 'is_open'),
              State('confidence-slider', 'value'),
              prevent_initial_call=True)
def reset_slider(modal_open, selected_confidence):
    """
    Resets the confidence slider value to 0.6 after closing the modal
    component

    Parameters
    ----------
    modal_open : bool
        A boolean that describes if the modal component is open or not
    selected_confidence : list of float
        The selected minimum and maximum values of the confidence slider

    Returns
    -------
    list of float
        The selected minimum and maximum values of the confidence slider
    """
    # modal window is closed so reset slider value
    if not modal_open:
        return [0, 0.6]

    return selected_confidence


# resets color-picker to black font color after closing the modal component
@app.callback(Output('color-picker', 'value'),
              Input('modal', 'is_open'),
              State('color-picker', 'value'),
              prevent_initial_call=True)
def reset_color_picker(modal_open, font_color):
    """
    Resets color-picker to black font color after closing the modal
    component

    Parameters
    ----------
    modal_open : bool
        A boolean that describes if the modal component is open or not
    font_color : dict of { 'hex': str,
                               'rgb': dict of { 'rgb' : 'r': int,
                                                        'g': int,
                                                        'b': int,
                                                        'a': int
                                              }
                             }
        The hex and rgb value of the selected font color

    Returns
    -------
    dict of { 'rgb': dict of { 'rgb' : 'r': int,
                                       'g': int,
                                       'b': int
                             }
            }
        The rgb value of the selected font color
    """
    # modal window is closed so reset font color
    if not modal_open:
        return dict(rgb=dict(r=0, g=0, b=0))

    return font_color


@app.callback(Output('collapse-body', 'is_open'),
              Input('collapse-button', 'n_clicks'),
              Input('modal', 'is_open'),
              State('collapse-body', 'is_open'),
              prevent_initial_call=True)
def toggle_collapse(n_clicks, modal_open, collapse_open):
    """
    Toggles visibility of collapse component on button click. Also
    hides collapse component when the modal component closes.

    Parameters
    ----------
    modal_open : bool
        A boolean that describes if the modal component is open or not
    collapse_open : bool
        A boolean that describes if the collapse component is visible
        or not

    Returns
    -------
    bool
        A boolean that describes if the collapse component is visible
        or not
    """
    # get the id of the component that triggered the callback
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'modal':
        if not modal_open:
            # modal component is closed so collapse the body
            return False

        # do nothing if modal component is opened
        return collapse_open

    if trigger == 'collapse-button':
        return not collapse_open
