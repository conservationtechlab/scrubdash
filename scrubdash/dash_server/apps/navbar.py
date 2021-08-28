"""This module contains the layout for the dashboard navbar."""

import dash_bootstrap_components as dbc
import dash_html_components as html

navbar = html.Div(
    [
        # Navbar for the logo.
        dbc.Navbar(
            html.A(
                # Use row and col to control vertical alignment
                # of logo / brand.
                dbc.Row(
                    dbc.Col(
                        html.Img(
                            src='../assets/sage-logo.png',
                            height='100px',
                            className='border-0'
                        )
                    ),
                    align='center',
                    no_gutters=True,
                ),
                href='/',
            ),
            color='white'
        ),
        # Navbar for links.
        dbc.NavbarSimple(
            [
                # Link to get back to the main page.
                dbc.NavItem(
                    dbc.NavLink(
                        'HOME',
                        href='/',
                        className='nav-link mr-2 ml-2'
                    )
                ),
                # Link to get back to a ScrubCam's labels grid.
                dbc.NavItem(
                    dbc.NavLink(
                        'LABELS',
                        id='nav-labels',
                        href='',
                        className='nav-link mr-2 ml-2'
                    ),
                    # Callbacks on the labels page, history page, and
                    # graphs page are responsible for changing the
                    # style display so the link is visible and has the
                    # correct href.
                    style={'display': 'none'}
                ),
                # Link to get back to a ScrubCam's graphs page.
                dbc.NavItem(
                    dbc.NavLink(
                        'GRAPHS',
                        id='nav-graphs',
                        href='',
                        className='nav-link mr-2 ml-2'
                    ),
                    # Callbacks on the labels page, history page, and
                    # graphs page are responsible for changing the
                    # style display so the link is visible and has the
                    # correct href.
                    style={'display': 'none'}
                )
            ],
            color='#215732'
        ),
    ]
)
