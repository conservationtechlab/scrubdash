"""
This file contains methods related to networking and sockets that are
used by the dash_server package.
"""

from datetime import datetime


def _get_time_difference(then):
    """
    Calculate the time difference between the input and the current time.

    Parameters
    ----------
    then : datetime time object
        The datetime of the time to calculate the difference from

    Returns
    -------
    dict of {
                'years': int,
                'days': int,
                'hours': int,
                'minutes': int,
                'seconds': int,
            }
        A dictionary containing the number of years, days, hours, minutes,
        and seconds that have elapsed between the input and the current
        time. The days, hours, minutes, and seconds are calculated as
        remainders from the immediate larger time interval. For example,
        the return would be something like 1 hour, 0 minutes, 0 seconds to
        denote that one hour has passed between the input and the current
        time. The dictionary does *not* return something like 1 hour, 60
        minutes, 3600 seconds (the interpretation that the dictionary
        contains the years, days, hours, etc representation of the time
        difference).

    Notes
    -----
    This method is adapted from the `getDuration` method provided in a
    post answered and edited from Sabito 錆兎 and Attaque on November 9,
    2017 and Febrary 15, 2021 to a stackoverflow thread here:
    https://stackoverflow.com/questions/1345827/how-do-i-find-the-time-difference-between-two-datetime-objects-in-python.
    """
    now = datetime.now()
    duration = now - then  # For build-in functions
    duration_in_s = duration.total_seconds()

    def years():
        return divmod(duration_in_s, 31536000)  # Seconds in a year=31536000.

    def days(seconds):
        return divmod(seconds if seconds is not None else duration_in_s, 86400)
        # Seconds in a day = 86400

    def hours(seconds):
        # Seconds in an hour = 3600
        return divmod(seconds if seconds is not None else duration_in_s, 3600)

    def minutes(seconds):
        # Seconds in a minute = 60
        return divmod(seconds if seconds is not None else duration_in_s, 60)

    def seconds(seconds):
        if seconds is not None:
            return divmod(seconds, 1)
        return duration_in_s

    y = years()
    d = days(y[1])  # Use remainder to calculate next variable
    h = hours(d[1])
    m = minutes(h[1])
    s = seconds(m[1])

    return {
        'years': int(y[0]),
        'days': int(d[0]),
        'hours': int(h[0]),
        'minutes': int(m[0]),
        'seconds': int(s[0]),
    }


def check_connection(then):
    """
    Check if a ScrubCam host is still connected to the asyncio server by
    checking the time difference between the input and the current time.

    Parameters
    ----------
    then : datetime time object
        The datetime of the time to calculate the difference from

    Returns
    -------
    tuple of str, CSS style dictionary
        A tuple that contains the connection status of the ScrubCam host
        and a CSS style style dictionary to format the status
    """
    time_diff = _get_time_difference(then)
    styles = {'color': '#d9534f', 'whiteSpace': 'pre-wrap'}

    if time_diff['years'] > 0:
        msg = ('DISCONNECTED\nLast online: {} year(s), {} day(s) ago'
               .format(time_diff['years'], time_diff['days']))
    elif time_diff['days'] > 0:
        msg = ('DISCONNECTED\nLast online: {} day(s), {} hours(s) ago'
               .format(time_diff['days'], time_diff['hours']))
    elif time_diff['hours'] > 0:
        msg = ('DISCONNECTED\nLast online: {} hours(s), {} minute(s) ago'
               .format(time_diff['hours'], time_diff['minutes']))
    elif time_diff['minutes'] > 0:
        msg = ('DISCONNECTED\nLast online: {} minute(s), {} second(s) ago'
               .format(time_diff['minutes'], time_diff['seconds']))
    elif time_diff['seconds'] > 20:
        # Check for 20 seconds instead of 15 seconds to allow for
        # a small amount of network latency.
        msg = ('DISCONNECTED\nLast online: {} second(s) ago'
               .format(time_diff['seconds']))
    else:
        msg = 'CONNECTED'
        styles['color'] = '#5cb85c'

    return (msg, styles)
