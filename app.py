# -*- coding: utf-8 -*-

# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

#!/usr/bin/env python3

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import base64

app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# retrieves the image as a base64 encoded string
with open('./assets/cheetah-1.jpg', 'rb') as image_file:
    cheetah_1 = base64.b64encode(image_file.read()).decode('ascii')

# second cheetah image to simulate image updates
with open('./assets/cheetah-2.jpg', 'rb') as image_file:
    cheetah_2 = base64.b64encode(image_file.read()).decode('ascii')

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

index_page = dbc.Container(
    [
        html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div([
                                    html.A([
                                        html.Img(id='cheetah-img', src='data:image/png;base64,{}'.format(cheetah_1), alt='cheetah')
                                    ], href='/cheetah'),    
                                    html.Div(html.Button(id='change-cheetah', n_clicks=0, children='Change Cheetah Image!'))
                                ])
                            ], width=4),
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('condor-1.jpg'), alt='condor')), width=4),
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('elephant-1.jpg'), alt='elephant')), width=4)
                    ],
                ),
                dbc.Row(
                    [
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('flamingo-1.jpg'), alt='flamingo')), width=4),
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('hippo-1.jpg'), alt='hippo')), width=4),
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('koala-1.jpg'), alt='koala')), width=4)
                    ],
                ),
                dbc.Row(
                    [
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('lion-1.jpg'), alt='lion')), width=4),
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('panda-1.jpg'), alt='panda')), width=4),
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('penguin-1.jpg'), alt='penguin')), width=4)
                    ],
                ),
                dbc.Row(
                    [
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('polar-bear-1.jpg'), alt='polar-bear')), width=4),
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('rhino-1.jpg'), alt='rhino')), width=4),
                        dbc.Col(html.Div(html.Img(src=app.get_asset_url('tortoise-1.jpg'), alt='tortoise')), width=4)
                    ],
                ),
            ]
        )
    ]
)

cheetah_page_layout = dbc.Container(
    html.Div([
        html.H1('Cheetah Images'),
        dbc.Row(
            [
                dbc.Col(html.Div(html.Img(id='cheetah-img', src='data:image/png;base64,{}'.format(cheetah_1), alt='cheetah', n_clicks=0)), width=6),
                dbc.Col(html.Div(html.Img(id='cheetah-img', src='data:image/png;base64,{}'.format(cheetah_2), alt='cheetah', n_clicks=0)), width=6),
            ]
        ),
        dcc.Link('Go back', href='/')
    ])
)

# change cheetah image callback
@app.callback(Output('cheetah-img', 'src'),
              Input('change-cheetah', 'n_clicks'), prevent_initial_call = True)
def change_cheetah(n_clicks):
    return('data:image/png;base64,{}'.format(cheetah_2))

# Update the index
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/cheetah':
        return cheetah_page_layout
    else:
        return index_page

if __name__ == '__main__':
    app.run_server(debug=True)
    # do a try except to catch keyboard interrupts
    # save and export csv on keyboard interrupts
