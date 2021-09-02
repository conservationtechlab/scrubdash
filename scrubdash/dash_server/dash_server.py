"""
This module contains high level callbacks that read messages from the
asyncio server and handles which pages to show based on the url.
"""

import logging
import re

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from scrubdash.dash_server.app import app
from scrubdash.dash_server.apps import (about_page, graphs_page,
                                        history_page, labels_page, main_page)
from scrubdash.dash_server.images import create_image_dict

log = logging.getLogger(__name__)


def start_dash(configs, asyncio_queue):
    """
    Start the dash server and control which page layout to render.

    Parameters
    ----------
    configs : str
        The dictionary of configuration settings obtained from loading a
        yaml config file
    asyncio_queue : multiprocessing.Queue
        The shared queue that allows communication between the asyncio
    """
    # Persistent variables allow the dash server to retain image
    # metadata when the browser is closed and/or reopened.
    DASH_IP = configs['DASH_SERVER_IP']
    DASH_PORT = configs['DASH_SERVER_PORT']
    global persistent_host_classes
    global persistent_host_images
    global persistent_host_image_logs
    global persistent_host_timestamps

    persistent_host_classes = {}
    persistent_host_images = {}
    persistent_host_image_logs = {}
    persistent_host_timestamps = {}

    app.layout = html.Div(
        [
            dcc.Location(id='url', refresh=False),
            dcc.Store(id='host-image-logs'),
            dcc.Store(id='host-images'),
            dcc.Store(id='host-classes'),
            dcc.Store(id='host-timestamps'),
            dcc.Interval(
                id='interval-component',
                interval=1.5 * 1000,  # in milliseconds
                n_intervals=0
            ),
            html.Div(id='page-content'),
            html.Div(id='hidden', style={'display': 'none'})
        ]
    )

    @app.callback(Output('host-image-logs', 'data'),
                  Output('host-images', 'data'),
                  Output('host-classes', 'data'),
                  Output('host-timestamps', 'data'),
                  Input('interval-component', 'n_intervals'))
    def update_host_dicts(n_intervals):
        """
        Check the shared queue with the asyncio server every 2 seconds
        to either update the a host's image dictionary if new images
        are received, update a host's image log path, or update a
        host's filter class list.

        Parameters
        ----------
        n_intervals : int
            The number of times the interval has passed

        Returns
        -------
        persistent_host_image_logs : dict of { 'hostname': str }
            A dictionary that contains the absolute path to each
            host's session image log
        persistent_host_images : dict of
                                 { 'hostname': dict of {'class_name': str} }
            A dictionary that contains the absolute path to most
            recent image for each class in a host's filter class list
        persistent_host_classes : dict of { 'hostname': list of str }
            A dictionary that contains the filter class list each host
        persistent_host_timestamps : dict of { 'hostname': float }
            A dictionary that contains the timestamp of the most recent
            heartbeat or message from each host
        """
        global persistent_host_classes
        global persistent_host_images
        global persistent_host_image_logs
        global persistent_host_timestamps

        while not asyncio_queue.empty():
            message = asyncio_queue.get()

            hostname = message['hostname']
            header = message['header']

            # There is no header check for 'CONNECTION' since a
            # 'CONNECTION' message only includes the heartbeat timestamp.
            # However, an 'INITIALIZE' and 'IMAGE' message also contain
            # the heartbeat timestamp, so obtaining the timestamp is not
            # conditional.  Thus, getting the timestamp is at the end of
            # the while loop and will be executed no matter the header
            # value.
            if header == 'INITIALIZE':
                # Retrieve class list.
                class_list = message['class_list']
                persistent_host_classes[hostname] = class_list

                # Get image log path.
                persistent_host_image_logs[hostname] = message['image_log']
                log_path = persistent_host_image_logs[hostname]

                # Create image dictionary.
                image_dict = create_image_dict(class_list, log_path)
                persistent_host_images[hostname] = image_dict

            elif header == 'IMAGE':
                filename = message['img_path']
                detected_classes = message['labels']

                # Update most recent image for relevant classes.
                host_filter_classes = persistent_host_classes[hostname]
                image_dict = persistent_host_images[hostname]
                for class_name in detected_classes:
                    if class_name in host_filter_classes:
                        image_dict[class_name] = filename

            # Get timestamp.
            persistent_host_timestamps[hostname] = message['timestamp']

        # The return value is not a tuple.  The return value is four
        # separate outputs, but they are grouped together with parens to
        # make flake8 happy since putting all the variables on one line
        # goes over 80 chars.
        return (persistent_host_image_logs, persistent_host_images,
                persistent_host_classes, persistent_host_timestamps)

    @app.callback(Output('page-content', 'children'),
                  Input('url', 'pathname'))
    def display_page(pathname):
        """
        Update the page content when the pathname of the url changes.

        Parameters
        ----------
        pathname : str
            The pathname of the url in window.location

        Returns
        -------
        Dash HTML Component
            A page layout written with Dash HTML Components
        """
        if pathname == '/':
            return main_page.layout
        # Matches with '/about'
        elif re.match('/about', pathname):
            return about_page.layout
        # Matches with '/[hostname]/graph'
        elif re.match('/[a-zA-Z0-9-]+/graphs', pathname):
            return graphs_page.layout
        # Matches with '/[hostname]/[class]'
        elif re.match('/[a-zA-Z0-9-]*/[a-zA-Z0-9_-]+', pathname):
            return history_page.layout
        # Matches with '/[hostname]'
        else:
            return labels_page.layout

    app.run_server(host=DASH_IP, port=DASH_PORT)

    # Don't need to catch KeyboardInterrupt since app.run_server catches
    # the keyboard interrupt to end the server.  Executing the following
    # log.info() means that the server has successfully closed.
    log.info('Successfully shut down dash server.')
