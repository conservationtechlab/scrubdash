"""This module contains the layout and callbacks for the graphs page."""

import logging
from datetime import datetime, timedelta

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.express as px
from dash.dependencies import Input, Output, State

from scrubdash.dash_server.app import app
from scrubdash.dash_server.apps.navbar import full_navbar
from scrubdash.dash_server.dataframe import transform_graphs_dataframe

log = logging.getLogger(__name__)

time_span = [
    {'label': '1 Hour', 'value': 'hour'},
    {'label': '1 Day', 'value': 'day'},
    {'label': '1 Week', 'value': 'week'},
    {'label': '1 Month', 'value': 'month'},
    {'label': '1 Year', 'value': 'year'},
    {'label': 'Max', 'value': 'max'}
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
    {'label': '1 Year', 'value': '1Y'}
]

layout = dbc.Container(
    [
        full_navbar,
        dbc.Container(
            [
                # Header.
                html.Div(
                    html.H1(
                        '',
                        id='graphs-header',
                        className='header px-5 pt-3',
                    ),
                    className='text-center py-2'
                ),
                # Description.
                html.P(
                    '',
                    id='graphs-desc',
                    className='gray-text text-center pb-4 mb-4 mt-1'
                ),
            ]
        ),
        # Aggregate Histogram by Class.
        dbc.Container(
            [
                html.H2(
                    'Aggregate Counts by Class',
                    className=('graph-header graph-divider '
                               'text-center px-5')
                ),
                html.Div(
                    [
                        dcc.Store(id='label-count'),
                        dcc.Dropdown(
                            id='agg-dropdown',
                            value=['All'],
                            multi=True,
                        )
                    ]
                ),
                html.Div(
                    # The actual histogram.
                    dcc.Graph(id='agg-histogram'),
                    className='mb-2'
                )
            ]
        ),
        # Histogram by Class, Time Span, and Time.
        # Unofficially referred to as the 'time histogram'.
        dbc.Container(
            [
                html.H2(
                    ('Looking at Images by Class, Time Span, and Time'
                        ' Interval'),
                    className=('graph-header graph-divider '
                               'text-center px-5 pb-4')
                ),
                # Class Dropdown.
                dbc.Row(
                    [
                        dbc.Col(
                            html.H5(
                                'Class:',
                                className='dark-gray'
                            ),
                            # Reponsive column widths for each
                            # screen size.
                            xs=2, sm=2, md=1, lg=1, xl=1
                        ),
                        dbc.Col(
                            dcc.Dropdown(
                                id='time-class',
                                value='All'
                            ),
                            # Reponsive column widths for each
                            # screen size.
                            xs=11, sm=10, md=11, lg=11, xl=11
                        )
                    ],
                    className='align-items-end pb-2 mb-2'
                ),
                # Time Span Dropdown.
                dbc.Row(
                    [
                        dbc.Col(
                            html.H5(
                                'Time Span to Graph:',
                                className='dark-gray mb-2'
                            ),
                            width=12
                        ),
                        dbc.Col(
                            dbc.RadioItems(
                                id='time-span',
                                className='btn-group',
                                labelClassName=('btn '
                                                'btn-outline-success'),
                                labelCheckedClassName='active',
                                options=time_span,
                                value='week'
                            )
                        )
                    ],
                    className='radio-group pb-2 mb-2'
                ),
                # Time Interval Dropdown.
                dbc.Row(
                    [
                        dbc.Col(
                            html.H5(
                                'Bucket Interval Size:',
                                className='dark-gray mb-2'
                            ),
                            width=12
                        ),
                        dbc.Col(
                            dbc.RadioItems(
                                id='bucket-interval',
                                className='btn-group',
                                labelClassName=('btn '
                                                'btn-outline-success'),
                                labelCheckedClassName='active',
                                options=time_intervals,
                                value='24H'
                            ),
                            # Reponsive column widths for each
                            # screen size.
                            xs=6, sm=6, md=6, lg=11, xl=11
                        )
                    ],
                    className='radio-group pb-2 mb-2'
                ),
                html.Div(
                    # The actual time histogram.
                    dcc.Graph(id='time-histogram'),
                )
            ],
            style={
                'padding-bottom': '40px'
            }
        )
    ],
    style={'max-width': '1250px'},
    fluid=True
)

no_results_fig = {
    'layout': {
        'xaxis': {
            'visible': False
        },
        'yaxis': {
            'visible': False
        },
        'annotations': [
            {
                'text': 'No matching data found',
                'xref': 'paper',
                'yref': 'paper',
                'showarrow': False,
                'font': {
                    'size': 28
                }
            }
        ]
    }
}


@app.callback(Output('graphs-header', 'children'),
              Output('graphs-desc', 'children'),
              Input('url', 'pathname'))
def update_graphs_header(pathname):
    """
    Update the graphs page header on page load or refresh.

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location

    Returns
    -------
    header : str
        The header for the graphs page that includes the hostname
    desc: str
        A description of what the graphs page shows
    """
    # Parse hostname.
    hostname = pathname.split('/')[1]
    header = hostname + ' Graphs'

    desc = ('This page features two histograms that will help you explore '
            'and visualize image data from the {} device.'.format(hostname))

    return header, desc


# host-classes must be an Input or else there will be callback problems.
# Passing 'host-classes' as a State will result in a None value on the
# initial call since there is no default 'data' value for host-classes.
@app.callback(Output('agg-dropdown', 'options'),
              Output('time-class', 'options'),
              Output('label-count', 'data'),
              Input('url', 'pathname'),
              Input('host-classes', 'data'),
              State('host-image-logs', 'data'))
def initialize_graphs_page(pathname, host_classes, host_image_logs):
    """
    Initialize the dropdown options for each histogram and creates the
    transformed dataframe for the histogram and time histogram.

    This callback is triggered when entering the graphs page or when
    refreshing the graphs page.

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location
    host_classes : dict of { 'hostname': list of str }
        A dictionary that contains the filter class list each host
    host_image_logs : dict of { 'hostname': str }
        A dictionary that contains the absolute path to each host's image
        log

    Returns
    -------
    dropdown_options : list of dict of { 'label': str, 'value': str }
        A list of dictionaries containing the label that renders as a
        dropdown option and the associated value for the backend
    json_result : json
        A json representation of the transformed dataframe used by the
        both histogram graphs
    """
    # Get the hostname.
    hostname = pathname.split('/')[1]

    # Get the ScrubCam specific filter class list and image log.
    filter_classes = host_classes[hostname]
    imagelog_path = host_image_logs[hostname]

    # Create the default options list.
    dropdown_options = [{'label': 'All', 'value': 'All'}]

    # Update the optoins list by adding a dropdown option for every
    # filter class.
    dropdown_options += [
        {
            'label': filter_class.capitalize(),
            'value': filter_class
        }
        for filter_class in filter_classes
    ]

    # Call helper method to create the transformed dataframe.
    flattened_df = transform_graphs_dataframe(imagelog_path)

    # Convert the pandas dataframe to json to be stored in dcc.Store.
    json_result = flattened_df.to_json(orient='index')

    return dropdown_options, dropdown_options, json_result


@app.callback(Output('agg-histogram', 'figure'),
              Input('agg-dropdown', 'value'),
              Input('label-count', 'data'))
def update_agg_histogram(selected_values, json_df):
    """
    Update the class shown in the histogram.

    This callback is triggered when either the dropdown value changes or
    the pandas dataframe changes.

    Parameters
    ----------
    selected_values : list of str
        The list of classes selected in the histogram dropdown
    json_df
        A json representation of the transformed dataframe used by the
        histogram and time graph

    Returns
    -------
    fig : plotly.express.histogram
        A plotly histogram object
    """
    # Convert the label-count data from a json to a pandas dataframe.
    df = pd.read_json(json_df, orient='index')

    if 'All' in selected_values:
        fig = px.histogram(df,
                           x='label',
                           title=('Count of all classes recorded in the '
                                  'image log'),
                           color_discrete_sequence=['green'])
        # Center the title.
        fig.update_layout(title_x=0.5)
    else:
        # Filter out rows whose label is different from the selected value.
        filtered_df = df[df['label'].isin(selected_values)]

        # No results found for selected class.
        if len(filtered_df) == 0:
            fig = no_results_fig
        # Results exist for the selected class.
        else:
            # Formatting the title.
            classes = ', '.join(selected_values)
            if len(selected_values) == 1:
                title = ('Count of the {} class recorded in the image log'
                         .format(classes))
            else:
                title = 'Count of the '
                i = 0
                while i < len(selected_values) - 2:
                    title += '{}, '.format(selected_values[i])
                    i += 1

                title += '{} and {} '.format(selected_values[i],
                                             selected_values[i+1])
                title += 'classes recorded in the image log'

            fig = px.histogram(filtered_df,
                               x='label',
                               title=title,
                               color_discrete_sequence=['green'])
            # Center the title.
            fig.update_layout(title_x=0.5)

    return fig


def _update_time_histogram_class(selected_class, df):
    """
    Update the class shown in the time histogram.

    Instead of directly updating the current histogram's selected class, this
    method creates a new histogram whose data is filtered by the selected
    class. Therefore the current histogram is not used at all and that is
    why it is not a parameter for this method.

    This method is a helper for update_time_histogram.

    Parameters
    ----------
    selected_class : str
        The selected class to show on the time histogram
    df : pandas.DataFrame
        The transformed dataframe used by the histogram and time histogram

    Returns
    -------
    fig : plotly.express.histogram
        A plotly histogram object
    """
    if selected_class == 'All':
        fig = px.histogram(df,
                           x='datetime',
                           histfunc='count',
                           title='Histogram for All Classes',
                           color_discrete_sequence=['green'])
    else:
        # Filter out rows whose label is different from the selected value.
        filtered_df = df[df['label'] == selected_class]
        fig = px.histogram(filtered_df,
                           x='datetime',
                           title='Histogram for the {} Class'
                           .format(selected_class.capitalize()),
                           color_discrete_sequence=['green'])

    # Center the title and create gaps between the buckets.
    fig.update_layout(bargap=0.2, title_x=0.5)

    return fig


def _update_time_histogram_x_axes(fig, selected_class, selected_span,
                                  selected_interval, df):
    """
    Update the domain and bucket size of the x-axis in the time histogram.

    This method is a helper for update_time_histogram.

    Parameters
    ----------
    fig : plotly.express.histogram
        A plotly histogram object
    selected_class : str
        The selected class to show on the time histogram
    selected_span : str
        The selected domain to show on the time histogram x-axis
    selected_interval : str
        The selected interval size to bin each bucket
    df
        The transformed dataframe used by the histogram and time histogram

    Returns
    -------
    fig : plotly.express.histogram
        An updated plotly histogram object
    """
    span_options = {
        'hour': timedelta(hours=1),
        'day': timedelta(days=1),
        'week': timedelta(days=7),
        'month': timedelta(days=31),
        'year': timedelta(days=365)
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

    # Check class.
    if selected_class == 'All':
        class_df = df
    else:
        class_df = df[df['label'] == selected_class]

    # Check time span.
    if selected_span == 'max':
        epoch_formatted = None
        filtered_df = class_df
    else:
        # epoch stands for the starting time of the selected span.
        epoch = now - span_options[selected_span]
        epoch_formatted = epoch.strftime('%Y-%m-%d %H:%M:%S')

        # Keep rows whose timestamp equal to or after the start of the epoch.
        filtered_df = class_df[class_df['timestamp'] >= epoch]

    # No results found for selected span.
    if len(filtered_df) == 0:
        fig = no_results_fig
    # Results exist in the selected span.
    else:
        time_interval = interval_options[selected_interval]

        # Update the x-axis domain and bin size.
        fig.update_traces(xbins_start=epoch_formatted,
                          xbins_size=time_interval)
        # tickmode='auto' improves x-axis labeling readability
        fig.update_xaxes(tickmode='auto')

    return fig


@app.callback(Output('time-histogram', 'figure'),
              Input('time-class', 'value'),
              Input('time-span', 'value'),
              Input('bucket-interval', 'value'),
              Input('label-count', 'data'))
def update_time_histogram(selected_class, selected_span,
                          selected_interval, json_df):
    """
    Update the time histogram when either the selected class, selected
    time span, or selected time interval dropdown option changes.

    Parameters
    ----------
    selected_class : str
        The selected class to show on the time histogram
    selected_span : str
        The selected domain to show on the time histogram x-axis
    selected_interval : str
        The selected interval size to bin each bucket
    json_df
        A json representation of the transformed dataframe used by the
        histogram and time histogram

    Returns
    -------
    plotly.express.histogram
        A plotly histogram object
    """
    # Convert the label-count data from a json to a pandas dataframe.
    df = pd.read_json(json_df, orient='index')
    fig = _update_time_histogram_class(selected_class, df)
    fig = _update_time_histogram_x_axes(fig,
                                        selected_class,
                                        selected_span,
                                        selected_interval,
                                        df)

    return fig
