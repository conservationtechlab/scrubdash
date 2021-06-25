import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import base64
import pandas as pd


def start_dash(queue):

    app = dash.Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True)

    app.layout = html.Div(
        [
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content')
        ]
    )

    index_page = dbc.Container(
        [
            html.Div(
                [
                    html.Div(
                        "Waiting to connect to scrubcam...",
                        id='grid-content'),
                    dcc.Store(id='image-dict', data={}, storage_type='local'),
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

    # Update the index
    @app.callback(Output('page-content', 'children'),
                  Input('url', 'pathname'))
    def display_page(pathname):
        if pathname == '/':
            return index_page
        else:
            return create_history_page(pathname)

    app.run_server()
