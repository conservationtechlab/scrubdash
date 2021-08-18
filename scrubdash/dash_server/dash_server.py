import logging

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from scrubdash.dash_server.app import app
from scrubdash.dash_server.apps import grid, history, graph, cam
from scrubdash.dash_server.utils import create_image_dict

log = logging.getLogger(__name__)

persistent_filter_classes = None


def start_dash(configs, asyncio_queue):
    """
    Starts the dash server and controls which page layout to render

    Parameters
    ----------
    asyncio_queue : multiprocessing.Queue
        The shared queue that allows communication between the asyncio
        server and dash server
    dash_ip : str
        The IP address the dash server renders the dashboard on
    dash_port : int
        The port number the dash server renders the dashboard on
    """
    # persistent variables allow dash server to retain image metadata
    # when the browser is closed and reopened
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

    # TODO: add host-timestamps to docstring parameters
    # checks shared queue every 2 seconds to update image dictionary.
    # also checks if filter classes list is passed (occurs only if
    # scrubcam connects after starting scrubdash.)
    @app.callback(Output('host-image-logs', 'data'),
                  Output('host-images', 'data'),
                  Output('host-classes', 'data'),
                  Output('host-timestamps', 'data'),
                  Input('interval-component', 'n_intervals'))
    def update_image_dict(n_intervals):
        """
        Checks the shared queue with the asyncio server every 2 seconds
        to either update the a host's image dictionary if new images
        are received, update a host's image log path, or update a
        host's filter class list

        Parameters
        ----------
        n_intervals : int
            The number of times the interval has passed

        Returns
        -------
        dict of { 'hostname': str }
            A dictionary that contains the absolute path to each
            host's image log
        dict of { 'hostname': dict of {'class_name': str} }
            A dictionary that contains the absolute path to most
            recent image for each class in a host's filter class list
        dict of { 'hostname': list of str }
            A dictionary that contains the filter class list each host
        """
        global persistent_host_classes
        global persistent_host_images
        global persistent_host_image_logs
        global persistent_host_timestamps

        while not asyncio_queue.empty():
            message = asyncio_queue.get()

            hostname = message['hostname']
            header = message['header']

            if header == 'INITIALIZE':
                # retrieve class list
                class_list = message['class_list']
                persistent_host_classes[hostname] = class_list

                # get image log path
                persistent_host_image_logs[hostname] = message['image_log']
                log_path = persistent_host_image_logs[hostname]

                # create image dictionary
                image_dict = create_image_dict(class_list, log_path)
                persistent_host_images[hostname] = image_dict

                # get timestamp
                persistent_host_timestamps[hostname] = message['timestamp']

            # short circuits out if image_dict is empty
            elif header == 'IMAGE':
                filename = message['img_path']
                detected_classes = message['labels']

                # filter out extraneous classes
                host_filter_classes = persistent_host_classes[hostname]
                image_dict = persistent_host_images[hostname]
                for class_name in detected_classes:
                    if class_name in host_filter_classes:
                        image_dict[class_name] = filename

                # get timestamp
                persistent_host_timestamps[hostname] = message['timestamp']

            elif header == 'CONNECTION':
                persistent_host_timestamps[hostname] = message['timestamp']

        log.info(persistent_host_timestamps)

        # the return value is not a tuple
        # the return value is four separate outputs, but they are
        # grouped together with parens to make flake8 happy since
        # putting all the variables on one line goes over 80 chars
        return (persistent_host_image_logs, persistent_host_images,
                persistent_host_classes, persistent_host_timestamps)

    # Update the page
    @app.callback(Output('page-content', 'children'),
                  Input('url', 'pathname'))
    def display_page(pathname):
        """
        Updates the page contents when the pathname of the url changes

        Parameters
        ----------
        pathname : str
            The pathname of the url in window.location

        Returns
        -------
        Dash HTML Component
            A page layout written with Dash HTML Components
        """
        # TODO: change to regex
        if pathname == '/':
            return cam.layout
        elif 'graph' in pathname:
            return graph.layout
        elif pathname.count('/') == 1:
            return grid.layout
        else:
            return history.layout

    app.run_server(host=DASH_IP, port=DASH_PORT)

    # don't need to catch KeyboardInterrupt since app.run_server() catches the
    # keyboard interrupt to end the server.
    # getting to log.info() means that the server has successfully closed.
    log.info('Successfully shut down dash server.')
