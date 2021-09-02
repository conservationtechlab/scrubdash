"""This module contains the layout for the dashboard navbar."""

import dash
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output

from scrubdash.dash_server.app import app

# Navbar for the logo.
logo_navbar = dbc.Navbar(
    [
        html.A(
            # Use row and col to control vertical alignment
            # of logo / brand.
            dbc.Row(
                dbc.Col(
                    html.Img(
                        src='../assets/scrubdash-logo.png',
                        height='100px',
                        className='border-0'
                    )
                ),
                align='center',
                no_gutters=True,
            ),
            href='/',
        ),
        html.Div(
            [
                html.A(
                    'GITHUB',
                    href='https://github.com/icr-ctl/scrubdash',
                    className='nav-link-secondary mr-4'
                ),
                html.A(
                    'ABOUT',
                    href='/about',
                    className='nav-link-secondary'
                )
            ],
            className='ml-auto mb-auto'
        ),
    ],
    color='white'
)

# This navbar only has a link to the home page. It is intended to be
# used for pages where the ScrubCam hostname is not known (eg. home
# page).
default_navbar = html.Div(
    [
        logo_navbar,
        dbc.NavbarSimple(
            # Link to get back to the main page.
            dbc.NavItem(
                dbc.NavLink(
                    'HOME',
                    href='/',
                    className='nav-link-primary mr-2 ml-2'
                )
            ),
            color='#215732'
        )
    ]
)


# This navbar has the complete set of links to the home page, labels
# page, and graphs page.  It is intended to be used for pages where the
# ScrubCam hostname is known (eg. labels page, graphs page, and history
# page).
full_navbar = html.Div(
    [
        logo_navbar,
        dbc.NavbarSimple(
            [
                # Link to get back to the main page.
                dbc.NavItem(
                    dbc.NavLink(
                        'HOME',
                        href='/',
                        className='nav-link-primary mr-2 ml-2'
                    )
                ),
                # Link to get back to a ScrubCam's labels grid.
                dbc.NavItem(
                    dbc.NavLink(
                        'LABELS',
                        id='nav-labels',
                        href='',
                        className='nav-link-primary mr-2 ml-2'
                    )
                ),
                # Link to get back to a ScrubCam's graphs page.
                dbc.NavItem(
                    dbc.NavLink(
                        'GRAPHS',
                        id='nav-graphs',
                        href='',
                        className='nav-link-primary mr-2 ml-2'
                    )
                )
            ],
            color='#215732'
        )
    ]
)


@app.callback(Output('nav-labels', 'href'),
              Output('nav-graphs', 'href'),
              Input('url', 'pathname'))
def update_full_navbar_links(pathname):
    """
    Update the links for the labels page and graphs page to be host
    specific.

    Parameters
    ----------
    pathname : str
        The pathname of the url in window.location

    Returns
    -------
    labels_href: HTML Anchor href attribute
        The href to the host's labels page
    graphs_href: HTML Anchor href attribute
        The href to the host's graphs page
    """
    # Matches the home page.
    if pathname == '/':
        no_update = dash.no_update
        return no_update, no_update
    # Matches the labels, graphs, and history pages.
    else:
        hostname = pathname.split('/')[1]
        labels_href = '/{}'.format(hostname)
        graphs_href = '/{}/graphs'.format(hostname)

        return labels_href, graphs_href
