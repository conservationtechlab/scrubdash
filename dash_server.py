import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import base64
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import logging

log = logging.getLogger(__name__)


def start_dash(queue):

    app = dash.Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True)

    app.layout = html.Div(
        [
            dcc.Location(id='url', refresh=False),
            dcc.Store(id='image-dict', data={}, storage_type='local'),
            html.Div(id='page-content')
        ]
    )

    index_page = dbc.Container(
        [
            html.Div(
                [
                    html.Div(
                        html.A("Graphs", href='/graphs')
                    ),
                    html.Div(
                        "Waiting to connect to scrubcam...",
                        id='grid-content'),
                    dcc.Interval(
                        id='interval-component',
                        interval=1.5 * 1000,  # in milliseconds
                        n_intervals=0
                    )
                ],
                id='index-content')
        ]
    )

    # function to update image dictionary
    def create_image_dict(class_list):
        # create empty image dictionary
        image_dict = {}

        # populate the image dictionary
        # initialize image path to most recent entry in image_log.csv
        df = pd.read_csv('image_log.csv')

        for classification in class_list:
            # resets the indices after dropping rows
            filtered = df[df['label'] == classification].reset_index(drop=True)
            # sorts paths in descending order (most recent to least recent)
            filtered.sort_values(ascending=False, by=['path'], inplace=True)

            # at least one image exists for this classification
            if len(filtered.index) > 0:
                # get most recent image (the first row since sorted by
                # desc order)
                image_dict[classification] = filtered.iloc[0].values[0]
            # no image exists for this classification
            else:
                image_dict[classification] = None

        return image_dict

    # checks shared queue every 2 seconds to update image dictionary
    @app.callback(Output('image-dict', 'data'),
                  Input('interval-component', 'n_intervals'),
                  State('image-dict', 'data'))
    def update_image_dict(n_intervals, image_dict):
        while not queue.empty():
            # block=False may be redundant since we already check if
            # the queue is empty so there's no chance of blocking
            message = queue.get(block=False)

            header = message['header']

            if header == 'CLASSES':
                class_list = message['class_list']
                image_dict = create_image_dict(class_list)
            # short circuits out if image_dict is empty
            elif image_dict and header == 'IMAGE':
                filename = message['img_path']
                class_name = message['label']
                image_dict[class_name] = filename

        # no change is made to image_dict if it is empty and an image
        # is received
        return image_dict

    # returns base64 encoding of image
    def get_base64_image(filename):
        base64_image = None
        if filename is None:
            return ""

        with open(filename, 'rb') as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('ascii')

        return base64_image

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
        # image base64 refernce: https://stackoverflow.com/questions/
        # 3715493/encoding-an-image-file-with-base64
        for class_name, filename in image_dict.items():
            base64_image = get_base64_image(filename)
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

    # creates grid of all images for the animal
    def create_history_page(pathname):
        # removes the '/' from the beginning of pathname
        animal = pathname[1:]
        h1_header = '{} Images'.format(animal.capitalize())

        # creating the history grid
        df = pd.read_csv('image_log.csv')

        # resets the indices after dropping rows
        filtered = df[df['label'] == animal].reset_index(drop=True)
        # sorts paths in descending order (most recent to least recent)
        filtered.sort_values(ascending=False, by=['path'], inplace=True)
        # gets a list of animal images
        image_list = filtered['path'].to_list()

        grid = []
        row = []
        col = 0

        # put 3 columns in a row
        # put 1 image per column
        for image in image_list:
            base64_image = get_base64_image(image)
            row.append(
                dbc.Col(
                    html.Div(
                        html.Img(
                            id=animal,
                            src='data:image/png;base64,{}'
                            .format(base64_image)))))
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

        history_page_layout = dbc.Container(
            html.Div(
                [
                    html.H1(h1_header),
                    html.Div(grid),
                    dcc.Link(
                        'Go back',
                        href='/')
                ]
            )
        )

        return history_page_layout

    # creates page to see visualizations of captured images
    def create_graph_page():
        df = pd.read_csv('image_log.csv')
        hist_fig = px.histogram(df, x="label")
        dropdown_options = [{'label': 'All', 'value': 'All'}]
        # adds dropdown option for every animal class
        dropdown_options += [
                                {
                                    'label': animal.capitalize(),
                                    'value': animal
                                }
                                for animal in df.label.unique()
                            ]

        time_span = [
            {'label': '1 Hour', 'value': 'hour'},
            {'label': '1 Day', 'value': 'day'},
            {'label': '1 Week', 'value': 'week'},
            {'label': '1 Month', 'value': 'month'},
            {'label': '1 Year', 'value': 'year'},
        ]

        time_intervals = [
            {'label': '30 Minutes', 'value': '30M'},
            {'label': '1 Hour', 'value': '1H'},
            {'label': '6 Hours', 'value': '6H'},
            {'label': '12 Hours', 'value': '12H'},
            {'label': '24 Hours', 'value': '24H'},
            {'label': '1 Week', 'value': '1W'},
            {'label': '1 Month', 'value': '1M'},
            {'label': '3 Months', 'value': '3M'},
            {'label': '6 Months', 'value': '6M'},
            {'label': '1 Year', 'value': '1Y'},
        ]

        day_in_ms = 1000 * 60 * 60 * 24
        now = datetime.now()
        start_time = now - timedelta(days=7)
        start_time_formatted = start_time.strftime('%Y-%m-%d')

        time_fig = px.histogram(df,
                                x="datetime",
                                histfunc="count",
                                title="Histogram on Date Axes")
        time_fig.update_traces(xbins_start=start_time_formatted,
                               xbins_size=day_in_ms)
        time_fig.update_xaxes(dtick=day_in_ms)

        graph_page_layout = html.Div([
            dbc.Container([
                html.H1('Aggregate Counts by Class'),
                dcc.Dropdown(
                    id='dropdown',
                    options=dropdown_options,
                    value='All'),
                dcc.Graph(id='histogram', figure=hist_fig)
            ]),
            dbc.Container([
                # specify string constant as number of pieces
                # necessary to make the string be under 80 col
                # ref:
                # https://stackoverflow.com/questions/1874592/how-to-write-very-long-string-that-conforms-with-pep8-and-prevent-e501
                html.H1(('Looking at Images by Class, Time Span, and Time '
                          'Interval')),
                html.Div([
                    html.P('Class:'),
                    dcc.Dropdown(
                        id='time-class',
                        options=dropdown_options,
                        value='All'
                    )
                ]),
                html.Div([
                    html.P('Time Span to Graph:'),
                    dcc.Dropdown(
                        id='time-span',
                        options=time_span,
                        value='week'
                    ),
                ]),
                html.Div([
                    html.P('Time Interval:'),
                    dcc.Dropdown(
                        id='time-interval',
                        options=time_intervals,
                        value='24H'
                    ),
                ]),
                dcc.Graph(id='time', figure=time_fig)
            ])
        ])

        return graph_page_layout

    # update histogram
    @app.callback(Output('histogram', 'figure'),
                  Input('dropdown', 'value'))
    def update_histogram(selected_value):
        df = pd.read_csv('image_log.csv')
        fig = None

        if selected_value == 'All':
            fig = px.histogram(df, x="label")
        else:
            filtered_df = df[df['label'] == selected_value]
            fig = px.histogram(filtered_df, x="label")

        return fig

    # helper function for update_time_graph
    # updates the class displayed
    def update_time_graph_class(fig, selected_class):
        df = pd.read_csv('image_log.csv')

        if selected_class == 'All':
            fig = px.histogram(df,
                               x="datetime",
                               histfunc="count",
                               title="Histogral for {} Class(es)"
                               .format(selected_class.capitalize()))
        else:
            filtered_df = df[df['label'] == selected_class]
            fig = px.histogram(filtered_df, x="datetime")

        fig.update_layout(bargap=0.2)
        return fig

    def update_time_graph_x_axes(fig, selected_span, selected_interval):
        span_options = {
            'hour': timedelta(hours=1),
            'day': timedelta(days=1),
            'week': timedelta(days=7),
            'month': timedelta(days=31),
            'year': timedelta(days=365),
        }

        interval_options = {
            '30M': 1000*60*30,
            '1H': 1000*60*60,
            '6H': 1000*60*60*6,
            '12H': 1000*60*60*12,
            '24H': 1000*60*60*24,
            '1W': 1000*60*60*24*7,
            '1M': 'M1',
            '3M': 'M3',
            '6M': 'M6',
            '1Y': 'M12'
        }

        now = datetime.now()

        start_time = now-span_options[selected_span]
        start_time_formatted = start_time.strftime('%Y-%m-%d')

        time_interval = interval_options[selected_interval]

        fig.update_traces(xbins_start=start_time_formatted,
                          xbins_size=time_interval)
        fig.update_xaxes(dtick=time_interval)

        return fig

    # update time series graph
    @app.callback(Output('time', 'figure'),
                  Input('time-class', 'value'),
                  Input('time-span', 'value'),
                  Input('time-interval', 'value'))
    def update_time_graph(selected_class, selected_span, selected_interval):
        fig = None
        fig = update_time_graph_class(fig, selected_class)
        fig = update_time_graph_x_axes(fig, selected_span, selected_interval)

        return fig

    # Update the page
    @app.callback(Output('page-content', 'children'),
                  Input('url', 'pathname'))
    def display_page(pathname):
        if pathname == '/':
            return index_page
        elif pathname == '/graphs':
            return create_graph_page()
        else:
            return create_history_page(pathname)

    app.run_server()

    # don't need to catch KeyboardInterrupt since app.run_server() catches the
    # keyboard interrupt to end the server.
    # getting to log.info() means that the server has successfully closed.
    log.info('Successfully shut down dash server.')
