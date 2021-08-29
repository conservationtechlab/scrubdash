"""This module contains the layout for the credits page."""

import logging

import dash_bootstrap_components as dbc
import dash_html_components as html

from scrubdash.dash_server.apps.navbar import default_navbar

log = logging.getLogger(__name__)

credits = 'The ScrubCam logo was created at LogoMakr.com'

layout = dbc.Container(
    [
        default_navbar,
        dbc.Container(
            [
                html.Div(
                    html.H1(
                        'Credits',
                        className='header light-green px-5 pt-3',
                    ),
                    className='text-center py-2'
                ),
                html.Div(
                    html.P(
                        [
                            'The ScrubDash logo was created at ',
                            html.A(
                                'LogoMakr.com',
                                href='https://logomakr.com/',
                                className='light-green'
                            )
                        ],
                        className='gray-text pb-4 mb-4 mt-1',
                        style={'display': 'inline-block'}
                    ),
                    className='text-center'
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
