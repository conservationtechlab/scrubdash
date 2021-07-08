import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import logging

from .app import app
from .apps import grid, history, graph
from .utils import create_image_dict

log = logging.getLogger(__name__)


def start_dash(queue):

    app.layout = html.Div(
        [
            dcc.Location(id='url', refresh=False),
            dcc.Store(id='image-dict', data={}, storage_type='local'),
            dcc.Interval(
                id='interval-component',
                interval=1.5 * 1000,  # in milliseconds
                n_intervals=0
            ),
            html.Div(id='page-content')
        ]
    )

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

    app.run_server()

    # don't need to catch KeyboardInterrupt since app.run_server() catches the
    # keyboard interrupt to end the server.
    # getting to log.info() means that the server has successfully closed.
    log.info('Successfully shut down dash server.')
