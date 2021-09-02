"""This module contains the layout for the credits page."""

import logging

import dash_bootstrap_components as dbc
import dash_html_components as html

from scrubdash.dash_server.apps.navbar import default_navbar

log = logging.getLogger(__name__)

credits = 'The ScrubCam logo was created at LogoMakr.com'

about_desc_1 = ('ScrubDash is a dashboard created with Plotly\'s Dash '
                'framework that organizes, visualizes, and analyzes images '
                'coming in from ScrubCams to facilitate remote population '
                'counting and tracking. Please visit our ')
about_desc_2 = ' to learn more about how ScrubDash works.'
github_href = 'https://github.com/icr-ctl/scrubdash'

kendrake_desc = ('Kendrake is a J.W. Sefton Summer Fellow (2021) and is the '
                 'developer of ScrubDash.')
jw_sefton_desc = ('The J.W. Sefton Foundation is a generous supporter of the '
                  'San Diego Zoo Wildlife Alliance Summer Student Fellowship '
                  'and helped create the opportunity to ScrubDash possible.')
ian_desc = ('Ian is a Senior Researcher in Population Sustainability who '
            'leads the Conservation Technology Lab and served as Kendrake\'s '
            'mentor during the 2021 fellowship.')

logo_desc = ('The ScrubDash logo depicts a sage that resembles the San '
             'Diego Sagewort, a plant found in the local desert scrub '
             'ecosystem that ScrubDash will be used in.')

layout = dbc.Container(
    [
        default_navbar,
        dbc.Container(
            [
                # About section.
                html.Div(
                    [
                        html.H1(
                            'About',
                            className='header px-5 pt-3 mb-3'
                        ),
                        html.P(
                            [
                                about_desc_1,
                                html.A(
                                    'GitHub',
                                    href=github_href,
                                    className='light-green'
                                ),
                                about_desc_2
                            ],
                            className='gray-text pb-4 mb-2 mt-1'
                        )
                    ],
                    className='text-center py-2'
                ),
                # Acknowledgements section.
                html.Div(
                    [
                        html.H1(
                            'Acknowledgements',
                            className='header px-5 pt-3'
                        ),
                        html.H3(
                            'Kendrake Tsui',
                            className='light-green mt-4'
                        ),
                        html.P(
                            kendrake_desc,
                            className='gray-text'
                        ),
                        html.H3(
                            'J.W. Sefton Foundation',
                            className='light-green mt-4'
                        ),
                        html.P(
                            jw_sefton_desc,
                            className='gray-text'
                        ),
                        html.H3(
                            'Ian Ingram',
                            className='light-green mt-4'
                        ),
                        html.P(
                            ian_desc,
                            className='gray-text'
                        )
                    ],
                    className='text-center pb-4 mb-2'
                ),
                # Our Logo section.
                html.Div(
                    [
                        html.H1(
                            'Our Logo',
                            className='header px-5 pt-3 mb-3'
                        ),
                        html.P(
                            logo_desc,
                            className='gray-text mb-3'
                        ),
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
                        )
                    ],
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
