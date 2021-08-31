"""This module contains the layout and callbacks for a label's history page."""

import ast
import base64
import csv
import logging
import math
import time
from datetime import date, datetime, timedelta
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
from scrubdash.dash_server.apps.navbar import full_navbar

log = logging.getLogger(__name__)

layout = dbc.Container(
    [
        full_navbar,
        # Store the current 3x3 page being shown.
        dcc.Store(id='page-index', data=1),
        dcc.Store(id='history-images-df'),
        dcc.Store(id='history-class'),
        # Header.
        html.Div(
            dbc.Container(
                [
                    html.Div(
                        html.H1(
                            '',
                            id='history-header',
                            className='header px-5 pt-3'
                        ),
                        className='text-center py-2'
                    ),
                    html.P(
                        '',
                        id='history-desc',
                        className='gray-text text-center pb-4 mb-4 mt-1'
                    ),
                    # Date range picker.
                    dbc.Row(
                        dbc.Col(
                            [
                                html.Div(
                                    html.H3(
                                        'Select a Date Range',
                                        className=('history-sub-header '
                                                   'text-center px-5')
                                    ),
                                    className='text-center py-2'
                                ),
                                dbc.Col(
                                    dcc.DatePickerRange(
                                        id='date-picker-range',
                                        min_date_allowed=date(2000, 1, 1),
                                        max_date_allowed=date(2099, 12, 31),
                                        initial_visible_month=date.today(),
                                        start_date=date(2020, 1, 1),
                                        end_date=date.today(),
                                        style={'margin': '0 auto'}
                                    ),
                                    className='text-center'
                                )
                            ]
                        )
                    )
                ],
                style={'padding-bottom': '50px'},
            ),
        ),
        # Error message when no images to show.
        dbc.Container(
            dbc.Row(
                dbc.Col(
                    dbc.Alert(
                        'No images to show',
                        id='no-images',
                        color='danger',
                        style={
                            'display': 'none',
                            'font-size': '36px'
                        }
                    )
                ),
                className='text-center'
            )
        ),
        # The 3x3 grid of images.
        dbc.Container(
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
                                                    'index': i
                                                },
                                                n_clicks=0,
                                                className='rounded'
                                            ),
                                            html.H4(
                                                id={
                                                    'type': 'sq-header',
                                                    'index': i
                                                },
                                                className='light-green pt-3',
                                            )
                                        ],
                                        className='text-center'
                                    )
                                ),
                                id={
                                    'type': 'grid-square',
                                    'index': i
                                },
                                className='pb-4 mt-1 mb-1',
                                # Reponsive column widths for each
                                # screen size.
                                xs=12, sm=6, md=6, lg=4, xl=4
                            )
                            # Create 9 squares.
                            for i in range(9)
                        ]
                    )
                ],
                id='history-grid'
            )
        ),
        # The modal component that shows the image rendered with
        # lboxes, the confidence slider, and the color picker.
        dbc.Modal(
            [
                dbc.ModalHeader(
                    html.H3(
                        id='modal-header',
                        className='history-sub-header px-3 mb-3'
                    ),
                    style={'margin': '0 auto'}
                ),
                dbc.ModalBody(
                    [
                        # The confidence slider.
                        html.Div(
                            [
                                dcc.RangeSlider(
                                    id='confidence-slider',
                                    min=0,
                                    max=100,
                                    step=0.5,
                                    marks={
                                        confidence: str(confidence)+'%'
                                        for confidence in range(0, 101, 5)
                                    },
                                    value=[0, 60],
                                    tooltip={'always_visible': True},
                                ),
                                html.Div(
                                    id='slider-output-container',
                                    className='gray-text pt-3 pb-4'
                                ),
                            ]
                        ),
                        # Where the image renders.
                        html.Div(
                            html.Img(
                                id='modal-img',
                                className='rounded'
                            ),
                            className='text-center'
                        ),
                        # Button that toggles the color picker collapse
                        # component.
                        html.Div(
                            dbc.Button(
                                'Pick font color',
                                id='collapse-button',
                                color='success',
                                n_clicks=0,
                            ),
                            className='text-center mt-3 mb-2',
                        ),
                        # The color picker.
                        dbc.Collapse(
                            daq.ColorPicker(
                                id='color-picker',
                                label=('Color Picker '
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
                        color='success',
                        n_clicks=0
                    )
                )
            ],
            id='modal',
            size='lg',
            is_open=False
        ),
        dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            # The back button to see the previous 3x3
                            # image page.
                            dbc.Button(
                                'Back',
                                id='prev-btn',
                                n_clicks=0,
                                color='success',
                                size='lg',
                                style={'display': 'none'}
                            ),
                            className='justify-content-start',
                            width=dict(size=2, order=1)
                        ),
                        dbc.Col(
                            # The next button to see the next 3x3 image grid.
                            dbc.Button(
                                'Next',
                                id='next-btn',
                                n_clicks=0,
                                color='success',
                                size='lg',
                                style={
                                    'display': 'none'
                                }
                            ),
                            className='justify-content-end',
                            width=dict(size=2, order=3)
                        ),
                        # This Col contains the page input box and
                        # shows many pages the user can cycle through.
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        # Text to render.
                                        'Page: ',
                                        # The page input component.
                                        dcc.Input(
                                            id='page-input',
                                            type='number',
                                            value=1,
                                            min=1,
                                            style=dict(width='65px')
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
                                    ],
                                    className='gray-text',
                                    id='page-input-div'
                                )
                            ],
                            className='text-center',
                            width=dict(size=8, order=2)
                        )
                    ],
                    className='align-items-center'
                ),
                dbc.Row(
                    # The error message that appears when the page
                    # input is out of range.
                    dbc.Col(
                        dbc.Alert(
                            id='page-error',
                            color='danger',
                            is_open=False,
                            style={'font-size': '24px'}
                        ),
                        className='text-center mt-3'
                    )
                )
            ],
            style={
                'padding-top': '15px',
                'padding-bottom': '50px'
            }
        )
    ],
    style={'max-width': '1250px'},
    fluid=True
)


@app.callback(Output('history-header', 'children'),
              Output('history-desc', 'children'),
              Input('url', 'pathname'))
def update_history_header(pathname):
    """
    Update the history page header on page load or refresh.

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location

    Returns
    -------
    header : str
        The page header describing the host and what label the history
        page shows
    desc : str
        A description of what the history page shows
    """
    # Parse hostname.
    hostname, label = pathname.split('/')[1], pathname.split('/')[2]
    header = hostname + ' || ' + label.capitalize() + ' History'

    desc = ('This page shows the history of {} images taken by the {} device. '
            'Change the start and end dates to filter which images are '
            'displayed. Click an image to see what objects were detected by '
            'the {} device.'.format(label, hostname, hostname))

    return header, desc


@app.callback(Output('history-images-df', 'data'),
              Output('total-pages', 'children'),
              Output('page-input', 'max'),
              Input('url', 'pathname'),
              Input('date-picker-range', 'start_date'),
              Input('date-picker-range', 'end_date'),
              State('host-image-logs', 'data'))
def initialize_history_page(pathname, start_date, end_date, host_logs):
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
    start_date : str
        A string representation of the starting date chosen on the date
        picker
    end_date : str
        A string representation of the ending date chosen on the date
        picker
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

    # Drop rows that do not contain the history class.
    filtered = (image_df[image_df['labels'].str
                .contains(image_class)])

    # Parse datetime from start_date.
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    # Add 1 day to selected end_date to include images taken on the end_date.
    end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

    # Convert datetime into unix timestamp.
    start_timestamp = time.mktime(start_date.timetuple())
    end_timestamp = time.mktime(end_date.timetuple())

    # Drop rows with timestamp outside the selected dates and reset the
    # indicies for sorting.
    filtered = (filtered[(filtered['timestamp'] >= start_timestamp) &
                         (filtered['timestamp'] <= end_timestamp)]
                .reset_index(drop=True))

    # Sorts paths in descending order (most recent to least recent).
    filtered.sort_values(ascending=False, by=['path'], inplace=True)

    # Convert the pandas dataframe to json so it can be stored in dcc.Store.
    json_result = filtered.to_json(orient='index')

    # Counts how many 3x3 grid pages are in the pandas dataframe.
    total_pages = math.ceil(len(filtered)/9)

    return json_result, total_pages, total_pages


@app.callback(Output({'type': 'sq-img', 'index': MATCH}, 'src'),
              Output({'type': 'sq-header', 'index': MATCH}, 'children'),
              Output({'type': 'grid-square', 'index': MATCH}, 'style'),
              Input({'type': 'sq-img', 'index': MATCH}, 'children'),
              Input({'type': 'sq-img', 'index': ALLSMALLER}, 'src'),
              Input('history-class', 'data'),
              Input('page-index', 'data'),
              State('history-images-df', 'data'),
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
    if len(filtered_df) == 0:
        image_list = []
    else:
        image_list = (filtered_df[['path', 'lboxes', 'datetime']]
                      .values.tolist())

    # Calculate the index of the image that triggered the callback.
    current_image_index = ((page - 1) * 9) + index
    # Calculate the total number of images in the dataframe.
    total_images = len(image_list)

    # The comparison operator is < and not <= since the image indices
    # start at 0 whereas the number of total images starts at 1. Therefore
    # the current_image_index must be strictly less than total_images.  We
    # must also check that total_images is not 0, which occurs when there
    # are no images to show.
    if current_image_index < total_images and total_images != 0:
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
    source_img = source_img.resize((round(1920 / 4), round(1080 / 4)))

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
    return ('You have selected a confidence interval of {}%-{}%'
            .format(values[0], values[1]))


@app.callback(Output('page-index', 'data'),
              Output('page-input', 'value'),
              Output('page-error', 'is_open'),
              Output('page-error', 'children'),
              Input('prev-btn', 'n_clicks'),
              Input('next-btn', 'n_clicks'),
              Input('page-input', 'value'),
              Input('history-images-df', 'data'),
              State('page-index', 'data'),
              State('total-pages', 'children'),
              prevent_initial_call=True)
def next_page(prev_btn, next_btn, page_input, json_df, page, total_pages):
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
    json_df
        A json representation of the transformed dataframe used by the
        history page
    page : int
        The current 3x3 grid page (pages are indexed at 1)
    total_pages : int
        The total number of 3x3 grid pages the user can cycle through

    Returns
    -------
    page : int or dash.no_update
        The updated page number after clicking on the `Next` or `Back`
        buttons
    alert_open : bool
        A boolean that describes if the alert component is open or not
    error_msg : str
        The error message displayed if the page input value is invalid
    """
    ctx = dash.callback_context

    # Get the id of the component that triggered the callback.
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    alert_open = False
    error_msg = ''

    if trigger == 'history-images-df':
        # Convert the history data from a json to a pandas dataframe.
        filtered_df = pd.read_json(json_df, orient='index')
        if len(filtered_df) == 0:
            # Set page count to 0 because there are no pages to show.
            # Setting the page to 0 is a hack that fixes a whole slew of
            # issues like not rendering the next or back buttons, and not
            # trying to render any images in the 3x3 grid.
            page = 0
        else:
            # Reset the page count back to 1.
            page = 1
    elif trigger == 'next-btn':
        page += 1
    elif trigger == 'prev-btn':
        page -= 1
    elif trigger == 'page-input':
        if page_input is None:
            # If the page input is invalid.  This means it is a
            # non-numeric value or the value is not within allowed
            # minimum-maximum range.
            page = dash.no_update
            alert_open = True
            error_msg = ('Error: The page must be between 1-{}'
                         .format(total_pages))
        elif page_input == page:
            # The user inputs the page currently being shown.
            page = dash.no_update
        else:
            # The user inputs a valid page that is not currently being
            # shown.
            page = page_input

    return page, page, alert_open, error_msg


@app.callback(Output('prev-btn', 'style'),
              Output('next-btn', 'style'),
              Input('page-index', 'data'),
              State('history-images-df', 'data'),
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
    if total_images > current_max_image_index and total_images != 0:
        render_next = True
    else:
        render_next = False

    # Check if there are previous images to show.
    if page > 1:
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
                # resets the slider values back to [0, 60] in the
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
            # Convert decimal into percent.
            confidence = float((lbox[1])) * 100

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

                # Truncate confidence to 3 deciaml places.
                draw.text((upper_left_corner),
                          '{}, {}'.format(class_name, '%.3f' % (confidence)),
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
    Reset the confidence slider range value to [0, 60] after closing the
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
        return [0, 60]

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
def toggle_color_picker_collapse(n_clicks, modal_open, collapse_open):
    """
    Toggle the visibility of the color picker collapse component.

    This callback also closes the collapse component when the modal
    component closes if the collapse component is not already closed.

    This callback is triggered when clicking the 'Pick font color' button
    in the modal window.

    Parameters
    ----------
    n_clicks : int
        The number of times the close button has been clicked on
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


@app.callback(Output('page-input-div', 'style'),
              Output('no-images', 'style'),
              Input('history-images-df', 'data'))
def render_no_images_to_show_message(json_df):
    """
    Determine whether to render the page input box or the 'No images to
    show' message.

    This callback utilizes the style attribute to make the page input
    element invisible and make the 'No images to show' message visible
    when no images exist in the pandas dataframe.

    This can happen if there are no images taken of a particular class at
    all, or if there are no images taken of a class within the selected
    start and end date.

    Parameters
    ----------
    json_df
        A json representation of the transformed dataframe used by the
        histogram and time graph

    Returns
    -------
    CSS Display Property
        A CSS display property specifying whether to render the page input
        box
    CSS Display Property
        A CSS display property specifying whether to render the 'No images
        to show' message
    """
    # Convert the history data from a json to a pandas dataframe.
    filtered_df = pd.read_json(json_df, orient='index')

    if len(filtered_df) == 0:
        input_style = {'display': 'none'}
        no_images_style = {'font-size': '36px'}
    else:
        input_style = {'display': 'inline'}
        no_images_style = {'display': 'none'}

    return input_style, no_images_style
