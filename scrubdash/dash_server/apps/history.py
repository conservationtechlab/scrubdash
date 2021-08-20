"""This module contains the layout and callbacks for a class history page."""

import ast
import base64
import csv
import logging
import math
from io import BytesIO

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_daq as daq
import dash_html_components as html
import numpy as np
import pandas as pd
from dash.dependencies import ALL, ALLSMALLER, MATCH, Input, Output, State
from PIL import Image, ImageDraw, ImageFont

from scrubdash.dash_server.app import app

log = logging.getLogger(__name__)

layout = dbc.Container(
    html.Div(
        [
            html.H1(id='history-header'),
            # Store the current 3x3 page being shown.
            dcc.Store(id='page-index', data=1),
            dcc.Store(id='history-images-df'),
            dcc.Store(id='history-class'),
            # The 3x3 grid of images.
            html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Spinner(
                                    html.Div(
                                        [
                                            html.Img(
                                                id={
                                                    'type': 'sq-img',
                                                    'index': j
                                                },
                                                n_clicks=0
                                            ),
                                            html.Div(
                                                id={
                                                    'type': 'sq-header',
                                                    'index': j
                                                }
                                            )
                                        ]
                                    )
                                ),
                                id={
                                    'type': 'grid-square',
                                    'index': j
                                },

                            )
                            # Create three consecutive indicies at a time.
                            # Eg. (1, 2, 3), (4, 5, 6), (7, 8, 9)
                            for j in range(i * 3, (i * 3) + 3)
                        ]
                    )
                    # Outer loop that bounds the value of j.
                    for i in range(3)
                ],
                id='history-grid',
            ),
            # The modal component that shows the image rendered with
            # lboxes, the confidence slider, and the color picker.
            dbc.Modal(
                [
                    dbc.ModalHeader(id='modal-header'),
                    dbc.ModalBody(
                        [
                            # The confidence slider.
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
                                ]
                            ),
                            # Where the image renders.
                            html.Img(
                                id='modal-img'
                            ),
                            # Button that toggles the collapse component.
                            dbc.Button(
                                "Pick font color",
                                id='collapse-button',
                                color='primary',
                                n_clicks=0
                            ),
                            # The color picker.
                            dbc.Collapse(
                                daq.ColorPicker(
                                    id='color-picker',
                                    label=('Color Picker'
                                           '(alpha value not supported)'),
                                    value=dict(rgb=dict(r=255, g=255, b=255))
                                ),
                                id='collapse-body',
                                is_open=False,
                            )
                        ],
                        id='modal-body'
                    ),
                    # The button to close the modal component.
                    dbc.ModalFooter(
                        dbc.Button(
                            'Close',
                            id='close',
                            className='ml-auto',
                            n_clicks=0
                        )
                    )
                ],
                id='modal',
                size='lg',
                is_open=False),
            # Back button to the classes page.
            html.Div(
                html.A(
                    id='hist-back-btn',
                    children='Go back to classes page',
                    href=''
                )
            ),
            # Back button to the hosts page.
            html.Div(
                html.A(
                    id='host-back-btn',
                    children='Go back to hosts page',
                    href='/'
                )
            ),
            html.Div(
                [
                    # The back button to see the previous 3x3 image page.
                    html.Button(
                        'Back',
                        id='prev-btn',
                        n_clicks=0,
                        style={'display': 'none'}
                    ),
                    # This div contains the page input box and shows many
                    # pages the user can cycle through.
                    html.Div(
                        [
                            # Text to render.
                            'Page ',
                            # The page input component.
                            dcc.Input(
                                id='page-input',
                                type='number',
                                value=1,
                                min=1
                            ),
                            # Text to render.
                            '/',
                            # Shows the total number of 3x3 pages.
                            html.P(
                                id='total-pages',
                                style={
                                    'display': 'inline'
                                }
                            ),
                            # The error message for invalid page input.
                            html.P(
                                id='page-error',
                                style={
                                    'display': 'inline',
                                    'color': 'red'
                                }
                            )
                        ]
                    ),
                    # The next button to see the next 3x3 image grid.
                    html.Button(
                        'Next',
                        id='next-btn',
                        n_clicks=0,
                        style={
                            'display': 'none'
                        }
                    )
                ],
                id='pages'
            )
        ]
    )
)


@app.callback(Output('hist-back-btn', 'href'),
              Input('url', 'pathname'))
def update_history_back_link(pathname):
    """
    Update the back link be host specific.

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location

    Returns
    -------
    href: HTML Anchor href attribute
        The href to the host's classes page.
    """
    # Parse hostname
    hostname = pathname.split('/')[1]

    # Create href.
    href = '/{}'.format(hostname)

    return href


@app.callback(Output('history-images-df', 'data'),
              Output('total-pages', 'children'),
              Output('page-input', 'max'),
              Input('url', 'pathname'),
              State('host-image-logs', 'data'))
def display_history_page(pathname, host_logs):
    """
    Initialize the history page by updating the history class and creating
    the image log dataframe.

    The image log dataframe is created by filtering the image log such
    that the remaining rows are images that contain an instance of the
    chosen history class.

    This callback is triggered when entering the history page or when
    refreshing the history page.

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location
    host_logs : dict of { 'hostname': str }
        A dictionary that contains the absolute path to each host's
        session image log

    Returns
    -------
    json_result : json
        A json representation of the transformed dataframe used by the
        histogram and time graph
    total_pages : int
        The total number of 3x3 grid pages the user can cycle through
    """
    # Parse hostname and image class.
    hostname = pathname.split('/')[1]
    image_class = pathname.split('/')[2]

    # Create the dataframe.
    log_path = host_logs[hostname]
    image_df = pd.read_csv(log_path)

    # Drop rows that do not contain the history class and reset the
    # indices for sorting.
    filtered = (image_df[image_df['labels'].str
                .contains(image_class)].reset_index(drop=True))
    # Sorts paths in descending order (most recent to least recent).
    filtered.sort_values(ascending=False, by=['path'], inplace=True)

    # Convert the pandas dataframe to json so it can be stored in dcc.Store.
    json_result = filtered.to_json(orient='index')

    # Counts how many 3x3 grid pages are in the pandas dataframe.
    total_pages = math.ceil(len(filtered)/9)

    return json_result, total_pages, total_pages


@app.callback(Output('history-header', 'children'),
              Input('url', 'pathname'))
def create_history_header(pathname):
    """
    Update the history page header.

    This callback is triggered when entering the history page or
    refreshing the history page.

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location

    Returns
    -------
    header : str
        The page header describing the host and what class the history
        page is for
    """
    # Parse hostname and image class.
    hostname = pathname.split('/')[1]
    image_class = pathname.split('/')[2]

    header = '{} || {} Images'.format(hostname, image_class.capitalize())

    return header


@app.callback(Output({'type': 'sq-img', 'index': MATCH}, 'src'),
              Output({'type': 'sq-header', 'index': MATCH}, 'children'),
              Output({'type': 'grid-square', 'index': MATCH}, 'style'),
              Input({'type': 'sq-img', 'index': MATCH}, 'children'),
              Input({'type': 'sq-img', 'index': ALLSMALLER}, 'src'),
              Input('history-class', 'data'),
              Input('page-index', 'data'),
              Input('history-images-df', 'data'),
              prevent_initial_call=True)
def create_history_grid(index_handle, prev_squares, pathname, page, json_df):
    """
    Update each image one by one in the 3x3 page when the page index,
    image log path, or history class changes.

    The functionality of this callback is very particular. The images in
    3x3 page update like dominoes falling down. This callback is triggered
    for the image with the smallest index when the page index changes.
    Updating the src of the image with the smallest index triggers this
    callback for the image with the second smallest index and so on until
    the last image src updates.

    This functionality allows the user to see when each image in the 3x3
    page updates when cycling through pages.

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
        history page

    Returns
    -------
    img_ src: str
        The source of the base64 encoded image
    header : str
        The image header (the image timestamp)
    display: CSS Display Property
        A CSS display property specifying whether to hide or show the
        grid square
    """
    index = dash.callback_context.inputs_list[0]['id']['index']

    # Convert the history data from a json to a pandas dataframe.
    filtered_df = pd.read_json(json_df, orient='index')

    # Gets a list containing the path, lboxes, and datetime for each image.
    image_list = filtered_df[['path', 'lboxes', 'datetime']].values.tolist()

    # Calculate the index of the image that triggered the callback.
    current_image_index = ((page - 1) * 9) + index
    # Calculate the total number of images in the dataframe.
    total_images = len(image_list)

    # The comparison operator is < and not <= since the image indices
    # start at 0 whereas the number of total images starts at 1. Therefore
    # the current_image_index must be strictly less than total_images.
    if current_image_index < total_images:
        # Image index is in the dataframe.
        image = image_list[current_image_index]
        image_path = image[0]
        source_img = Image.open(image_path).convert('RGB')
        header = image[2]
        display = {'display': 'inline-block'}
    else:
        # Image index is not in dataframe (it's out of bounds).  Therefore
        # we return a white frame and hide its display.
        white_frame = 255 * np.ones((1000, 1000, 3), np.uint8)
        source_img = Image.fromarray(white_frame)
        header = ''
        display = {'display': 'none'}

    # Resize image to show in the 3x3 grid.
    source_img = source_img.resize((round(1920 / 8), round(1080 / 8)))

    # Create a temporary buffer to get image binary.
    buffer = BytesIO()
    source_img.save(buffer, format='JPEG')
    # Get the bytes of the resized image.
    img_data = buffer.getvalue()
    base64_image = base64.b64encode(img_data).decode('ascii')
    img_src = 'data:image/jpeg;base64,{}'.format(base64_image)

    return img_src, header, display


@app.callback(Output('slider-output-container', 'children'),
              Input('confidence-slider', 'value'))
def slider_value(values):
    """
    Show the slider range values in the modal window.

    Parameters
    ----------
    values : list of float
        The selected minimum and maximum values of the confidence slider

    Returns
    -------
    str
        A message displaying the selected confidence range
    """
    return 'You have selected a confidence interval of: {}'.format(values)


@app.callback(Output('page-index', 'data'),
              Output('page-input', 'value'),
              Output('page-error', 'children'),
              Input('prev-btn', 'n_clicks'),
              Input('next-btn', 'n_clicks'),
              Input('page-input', 'value'),
              State('page-index', 'data'),
              State('total-pages', 'children'),
              prevent_initial_call=True)
def next_page(prev_btn, next_btn, page_input, page, total_pages):
    """
    Update the page index when clicking the `Next` or `Back` buttons.

    Parameters
    ----------
    prev_btn : int
        The number of times the button has been clicked on
    next_btn : int
        The number of times the button has been clicked on
    page_input : int
        The user input specifying what 3x3 page they want to see
    page : int
        The current 3x3 grid page (pages are indexed at 1)
    total_pages : int
        The total number of 3x3 grid pages the user can cycle through

    Returns
    -------
    page : int or dash.no_update
        The updated page number after clicking on the `Next` or `Back`
        buttons
    error_msg : str
        The error message displayed if the page input value is invalid
    """
    ctx = dash.callback_context

    # Get the id of the component that triggered the callback.
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger == 'next-btn':
        page += 1
    elif trigger == 'prev-btn':
        page -= 1
    elif trigger == 'page-input':
        if page_input is None:
            # If the page input is invalid.  This means it is a
            # non-numeric value or the value is not within allowed
            # minimum-maximum range.
            page = dash.no_update
            error_msg = ('Error: The page must be between 1-{}'
                         .format(total_pages))
        elif page_input == page:
            # The user inputs the page currently being shown.
            page = dash.no_update
            error_msg = ''
        else:
            # The user inputs a valid page that is not currently being
            # shown.
            page = page_input
            error_msg = ''

    return page, page, error_msg


@app.callback(Output('prev-btn', 'style'),
              Output('next-btn', 'style'),
              Input('page-index', 'data'),
              Input('history-images-df', 'data'),
              prevent_initial_call=True)
def render_buttons(page, json_df):
    """
    Determine whether to render the `Next` and `Back` buttons.

    The `Next` button is rendered if there are more images to show. The
    `Back` button is rendered if there are previous images to show.

    Parameters
    ---------
    page : int
        The current 3x3 grid page (pages are indexed at 1)
    json_df
        A json representation of the transformed dataframe used by the
        history page

    Returns
    -------
    CSS Display Property
        A CSS display property specifying whether to render the `Back`
        button
    CSS Display Property
        A CSS display property specifying whether to render the `Next`
        button
    """
    # Convert the history data from a json to a pandas dataframe.
    image_df = pd.read_json(json_df, orient='index')
    # Calculate the total number of images in the dataframe.
    total_images = len(image_df)

    # Calculate the largest index in the 3x3 page currently shown.
    current_max_image_index = page * 9

    # Checks to see if there are more images to show.
    if total_images >= current_max_image_index:
        render_next = True
    else:
        render_next = False

    # Check if there are previous images to show.
    if page > 0:
        render_prev = True
    else:
        render_prev = False

    if render_prev and render_next:
        # Render both buttons.
        render_results = ({'display': 'inline-block', 'float': 'left'},
                          {'display': 'inline-block', 'float': 'right'})
    elif render_prev:
        # Render only the previous button.
        render_results = ({'display': 'inline-block', 'float': 'left'},
                          {'display': 'none'})
    elif render_next:
        # Render only the next button.
        render_results = ({'display': 'none'},
                          {'display': 'inline-block', 'float': 'right'})
    else:
        # Render neither buttons.
        render_results = ({'display': 'none'}, {'display': 'none'})

    return render_results[0], render_results[1]


# TODO: see if there are helper methods to abstract similar code between
# toggle_modal and create_history_grid
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
              State('history-images-df', 'data'),
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
        The header of the modal component. This is the timestamp of the
        image rendered in the modal component
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
        A base64 encoded image source of the image to be rendered in the
        modal component
    str
        The header of the modal component. This is the timestamped of
        the image rendered in the modal component
    """
    ctx = dash.callback_context

    # Get the id of the component that triggered the callback.
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]

    try:
        # Trigger was clicking on an image (a sq-img component).
        square = ast.literal_eval(trigger)['index']
    except ValueError:
        # Trigger was the close button.
        if trigger == 'close':
            # Close the window, empty the img src, and empty the img header.
            return False, '', ''

        if trigger == 'confidence-slider':
            if not modal_open:
                # The modal window is closed so do nothing.  This
                # condition happens when the user clicks outside the modal
                # window to close the component.  Closing the modal window
                # resets the slider values back to [0, 0.6] in the
                # reset_slider callback.  We just return the modal_open
                # value back to keep it closed.
                return modal_open, '', ''

            # Find square index of the image to show in the modal window.
            np_img_headers = np.array(img_headers)
            square = int(np.where(np_img_headers == modal_header)[0][0])

        if trigger == 'color-picker':
            # Find square index of the image to show in the modal window.
            np_img_headers = np.array(img_headers)
            square = int(np.where(np_img_headers == modal_header)[0][0])

    # Get the timestamp of the clicked image.
    timestamp = img_headers[square]

    # Get the image's path.
    image_df = pd.read_json(json_df, orient='index')
    filtered_df = image_df[image_df['datetime'] == timestamp]
    image_list = filtered_df[['path', 'lboxes', 'datetime']].values.tolist()
    image = image_list[0]
    image_path = image[0]

    # Open the image as bytes so we can draw lboxes on it.
    source_img = Image.open(image_path).convert('RGB')
    draw = ImageDraw.Draw(source_img)

    # Get csv containing the lboxes.
    lbox_csv_path = image[1]

    # Get the confidence min and max from the range slider.
    confidence_min = selected_confidence[0]
    confidence_max = selected_confidence[1]

    # Get the rgb value from the color picker.
    rgb = font_color['rgb']
    font_color = (rgb['r'], rgb['g'], rgb['b'])

    # Draw lboxes onto the image.
    with open(lbox_csv_path, newline='') as lboxes:
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

    # Resize the image to show in the modal component.
    source_img = source_img.resize((round(1920 / 2), round(1080 / 2)))

    # Create a temporary buffer to get image binary.
    buffer = BytesIO()
    source_img.save(buffer, format='JPEG')
    # Get the bytes of the resized image.
    img_data = buffer.getvalue()
    base64_image = base64.b64encode(img_data).decode('ascii')
    img_src = 'data:image/jpeg;base64,{}'.format(base64_image)

    return True, img_src, image[2]


@app.callback(Output('confidence-slider', 'value'),
              Input('modal', 'is_open'),
              State('confidence-slider', 'value'),
              prevent_initial_call=True)
def reset_slider(modal_open, selected_confidence):
    """
    Reset the confidence slider range value to [0, 0.6] after closing the
    modal component.

    Parameters
    ----------
    modal_open : bool
        A boolean that describes if the modal component is open or not
    selected_confidence : list of float
        The selected minimum and maximum values of the confidence slider

    Returns
    -------
    list of float
        The default minimum and maximum values of the confidence slider
    """
    # The modal window is closed so reset the slider values.
    if not modal_open:
        return [0, 0.6]

    # The modal window is open so return the current slider values.
    return selected_confidence


# resets color-picker to black font color after closing the modal component
@app.callback(Output('color-picker', 'value'),
              Input('modal', 'is_open'),
              State('color-picker', 'value'),
              prevent_initial_call=True)
def reset_color_picker(modal_open, font_color):
    """
    Reset the color-picker to white font color after closing the modal
    component.

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
    # The modal window is closed so reset the font color.
    if not modal_open:
        return dict(rgb=dict(r=255, g=255, b=255))

    # The modal window is open so return the current font color.
    return font_color


@app.callback(Output('collapse-body', 'is_open'),
              Input('collapse-button', 'n_clicks'),
              Input('modal', 'is_open'),
              State('collapse-body', 'is_open'),
              prevent_initial_call=True)
def toggle_collapse(n_clicks, modal_open, collapse_open):
    """
    Toggle the visibility of collapse component.

    This callback also closes collapse component when the modal component
    closes if the collapse component is not already closed.

    This callback is triggered when clicking the 'Pick font color' button
    in the modal window.

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
    ctx = dash.callback_context

    # Get the id of the component that triggered the callback.
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger == 'modal':
        if not modal_open:
            # The modal component is closed so collapse the body.
            return False

        # The modal component is open so do nothing.
        return collapse_open

    if trigger == 'collapse-button':
        return not collapse_open
