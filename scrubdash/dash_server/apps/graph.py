import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import logging
import ast

from scrubdash.dash_server.app import app

log = logging.getLogger(__name__)

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

layout = html.Div([
    dbc.Container([
        html.H1('Aggregate Counts by Class'),
        dcc.Store(id='label-count'),
        dcc.Dropdown(
            id='dropdown',
            value='All'),
        dcc.Graph(id='histogram')
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
        html.Div([
            dcc.Graph(id='time-graph'),
        ])
    ])
])


# Initializes the dropdown options when entering the graph page.
# 'filter-classes' must be an Input or else there will be callback problems.
# Passing 'filter-classes' as a State will result in a None value on the
# initial call since there is no default 'data' value for 'filter-classes'
@app.callback(Output('dropdown', 'options'),
              Output('time-class', 'options'),
              Output('label-count', 'data'),
              Input('url', 'pathname'),
              Input('filter-classes', 'data'),
              State('image-dict', 'data'),
              State('log-path', 'data'))
def initialize_graph_page(pathname, filter_classes, image_dict, log_path):
    # create options list
    dropdown_options = [{'label': 'All', 'value': 'All'}]

    # adds dropdown option for every filter_class
    dropdown_options += [
        {
            'label': filter_class.capitalize(),
            'value': filter_class
        }
        for filter_class in filter_classes
    ]

    # create dataframe of label counts from image log
    df = pd.read_csv(log_path)
    # transform cell content from str to list
    labels_col = df['labels'].apply((lambda arr: ast.literal_eval(arr)))
    labels_col = labels_col.to_list()
    timestamp_col = df['timestamp'].to_list()
    datetime_col = df['datetime'].to_list()

    # create dataframe that flattens each label into its own row with its
    # datetime
    data = []

    for row_index in range(len(labels_col)):
        labels = labels_col[row_index]
        timestamp = timestamp_col[row_index]
        datetime_entry = datetime_col[row_index]
        for label in labels:
            data += [[label, timestamp, datetime_entry]]

    label_df = pd.DataFrame(data, columns=['label', 'timestamp', 'datetime'])

    # converts the pandas dataframe to json to be stored in dcc.Store()
    json_result = label_df.to_json(orient='index')

    return dropdown_options, dropdown_options, json_result


# update histogram
@app.callback(Output('histogram', 'figure'),
              Input('dropdown', 'value'),
              Input('label-count', 'data'))
def update_histogram(selected_value, json_df):
    # converts label-count from a json to a pandas dataframe
    df = pd.read_json(json_df, orient='index')

    fig = None

    if selected_value == 'All':
        fig = px.histogram(df,
                           x="label",
                           title="Count of all classes recorded in the "
                                 "image log")
    else:
        filtered_df = df[df['label'] == (selected_value)]
        fig = px.histogram(filtered_df,
                           x="label",
                           title="Count of {} class recorded in the image log"
                                 .format(selected_value))

    return fig


# helper function for update_time_graph
# updates the class displayed
def update_time_graph_class(fig, selected_class, df):
    if selected_class == 'All':
        fig = px.histogram(df,
                           x="datetime",
                           histfunc="count",
                           title="Histogram for All Classes")
    else:
        filtered_df = df[df['label'] == selected_class]
        fig = px.histogram(filtered_df,
                           x="datetime",
                           title="Histogram for {} Class"
                           .format(selected_class.capitalize()))

    fig.update_layout(bargap=0.2)

    return fig


def update_time_graph_x_axes(fig, selected_span, selected_interval, df):
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

    start_time = now - span_options[selected_span]
    filtered_df = df[df['timestamp'] >= start_time]

    # No results found for selected span
    if len(filtered_df) == 0:
        fig = {
            "layout": {
                "xaxis": {
                    "visible": False
                },
                "yaxis": {
                    "visible": False
                },
                "annotations": [
                    {
                        "text": "No matching data found",
                        "xref": "paper",
                        "yref": "paper",
                        "showarrow": False,
                        "font": {
                            "size": 28
                        }
                    }
                ]
            }
        }
    # Results exist in selected span
    else:
        start_time_formatted = start_time.strftime('%Y-%m-%d %H:%M:%S')

        time_interval = interval_options[selected_interval]

        # TODO: update tick intervals to be readable
        # https://plotly.com/python/tick-formatting/
        fig.update_traces(xbins_start=start_time_formatted,
                          xbins_size=time_interval)
        # tickmode='auto' may be a good fix to improve readability
        fig.update_xaxes(tickmode='auto')

    return fig


# update time series graph
@app.callback(Output('time-graph', 'figure'),
              Input('time-class', 'value'),
              Input('time-span', 'value'),
              Input('time-interval', 'value'),
              Input('label-count', 'data'))
def update_time_graph(selected_class, selected_span,
                      selected_interval, json_df):

    # converts label-count from a json to a pandas dataframe
    df = pd.read_json(json_df, orient='index')
    fig = None
    fig = update_time_graph_class(fig, selected_class, df)
    fig = update_time_graph_x_axes(fig, selected_span, selected_interval, df)

    return fig
