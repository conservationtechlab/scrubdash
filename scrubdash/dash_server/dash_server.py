import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import logging

from scrubdash.dash_server.app import app
from scrubdash.dash_server.apps import grid, history, graph
from scrubdash.dash_server.utils import create_image_dict

log = logging.getLogger(__name__)

persistent_filter_classes = None


def start_dash(queue, log_path, filter_classes, dash_ip, dash_port):

    # necessary for when the actual list for filter_classes is not available on
    # dash start-up since scrubcam has not connected to asyncio yet. However,
    # we want dash to be running anyway so the "waiting to connect to
    # scurbdash..." page can be shown to the user.
    global persistent_filter_classes
    persistent_filter_classes = filter_classes

    app.layout = html.Div(
        [
            dcc.Location(id='url', refresh=False),
            dcc.Store(id='log-path'),
            dcc.Store(id='image-dict'),
            dcc.Store(id='filter-classes'),
            dcc.Interval(
                id='interval-component',
                interval=1.5 * 1000,  # in milliseconds
                n_intervals=0
            ),
            html.Div(id='page-content'),
            html.Div(id='hidden', style={'display': 'none'})
        ]
    )

    # callback should only be triggered on initial load since the trigger is
    # hidden and cannot be clicked on
    @app.callback(Output('log-path', 'data'),
                  Input('hidden', 'n_clicks'))
    def get_log_path(n_clicks):
        return log_path

    # checks shared queue every 2 seconds to update image dictionary.
    # also checks if filter classes list is passed (occurs only if scrubcam
    # connects after starting scrubdash.)
    @app.callback(Output('image-dict', 'data'),
                  Output('filter-classes', 'data'),
                  Input('interval-component', 'n_intervals'),
                  State('image-dict', 'data'))
    def update_image_dict(n_intervals, image_dict):
        while not queue.empty():
            # block=False may be redundant since we already check if
            # the queue is empty so there's no chance of blocking
            global persistent_filter_classes
            message = queue.get(block=False)

            header = message['header']

            if header == 'CLASSES':
                class_list = message['class_list']
                persistent_filter_classes = class_list
                image_dict = create_image_dict(class_list, log_path)
            # short circuits out if image_dict is empty
            elif image_dict and header == 'IMAGE':
                filename = message['img_path']
                detected_classes = message['labels']

                # filter out extraneous classes
                for class_name in detected_classes:
                    if class_name in persistent_filter_classes:
                        image_dict[class_name] = filename

        # error catch: no change is made to image_dict if it is empty and an
        # image is received
        if not image_dict:
            image_dict = create_image_dict(persistent_filter_classes, log_path)

        # persistent_filter_classes only changes if header == 'CLASSES'
        return image_dict,  persistent_filter_classes

    # Update the page
    @app.callback(Output('page-content', 'children'),
                  Input('url', 'pathname'))
    def display_page(pathname):
        if pathname == '/':
            return grid.layout
        elif pathname == '/graphs':
            return graph.layout
        else:
            return history.layout

    app.run_server(host=dash_ip, port=dash_port)

    # don't need to catch KeyboardInterrupt since app.run_server() catches the
    # keyboard interrupt to end the server.
    # getting to log.info() means that the server has successfully closed.
    log.info('Successfully shut down dash server.')
