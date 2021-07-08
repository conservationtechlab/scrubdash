import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import logging

from ..app import app

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
        dcc.Graph(id='time-graph'),
    ])
])


# Initializes the dropdown options when entering the graph page
@app.callback(Output('dropdown', 'options'),
              Output('time-class', 'options'),
              Input('url', 'pathname'))
def initialize_graph_page(pathname):
    df = pd.read_csv('image_log.csv')

    dropdown_options = [{'label': 'All', 'value': 'All'}]

    # adds dropdown option for every animal class
    dropdown_options += [
                            {
                                'label': animal.capitalize(),
                                'value': animal
                            }
                            for animal in df.label.unique()
                        ]

    return dropdown_options, dropdown_options


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
@app.callback(Output('time-graph', 'figure'),
              Input('time-class', 'value'),
              Input('time-span', 'value'),
              Input('time-interval', 'value'))
def update_time_graph(selected_class, selected_span, selected_interval):
    fig = None
    fig = update_time_graph_class(fig, selected_class)
    fig = update_time_graph_x_axes(fig, selected_span, selected_interval)

    return fig
