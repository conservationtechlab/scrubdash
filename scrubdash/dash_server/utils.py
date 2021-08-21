"""This file contains utility methods used by the dash_server package."""

import ast
from datetime import datetime

import pandas as pd


def create_image_dict(class_list, image_log):
    """
    Create a ScrubCam host's image dictionary on connection.

    Parameters
    ----------
    class_list : list of str
        The list of classes the scrubcam filters images for
    image_log : str
        The absolute path of the image log for the current user session

    Returns
    -------
    image_dict : dict of { 'class_name' : str }
        An updated dictionary that maps the most recent image for each
        each class_name. The image is represented as the absolute path
        to the image
    """
    df = pd.read_csv(image_log)

    # Create empty image dictionary.
    image_dict = {}

    # Populate the image dictionary by initializing the each class' image
    # path its most recent entry in the image log.
    for classification in class_list:
        # Drop rows that do not contain the history class and reset the
        # indices for sorting.
        filtered = (df[df['labels'].str.contains(classification)]
                    .reset_index(drop=True))
        # Sorts paths in descending order (most recent to least recent).
        filtered.sort_values(ascending=False, by=['path'], inplace=True)

        # At least one image exists for this class.
        if len(filtered.index) > 0:
            # Get the most recent image (the first row since the df is
            # sorted by desc order).
            image_dict[classification] = filtered.iloc[0].values[0]
        # No image exists for this class.
        else:
            image_dict[classification] = None

    return image_dict


def get_time_difference(then):
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
    time_diff = get_time_difference(then)
    styles = {'color': 'red', 'whiteSpace': 'pre-wrap'}

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
        styles['color'] = 'green'

    return (msg, styles)


def transform_graphs_dataframe(imagelog_path):
    """
    Create a transformed dataframe to be used by the graphs page.

    The transformed dataframe is created by creating a row for each class
    detected in every image. The image log currently creates a row for
    each image and records all the detected classes in a list in the
    'labels' column. To have the flexibility to graph histograms for each
    class, we need to create a dataframe where each row corresponds to a
    single detected class, not a list of detected classes. Thus, each list
    in the 'labels' column must be flattened such that each class in the
    list is on a different row with its own timestamp and datetime.

    As an example, the list ['person', 'dog', 'cat'] must be flattened
    into three rows, similar to a sturcture like this: [['person'],
    ['dog'], ['cat]] (omitted flattening the timestamp and datetime for
    simplicity).

    Parameters
    ----------
    imagelog_path : str
        The absolute path to a ScrubCam host's session image log.

    Returns
    -------
    flattened_df : pandas.DataFrame
        The transformed dataframe used by the histogram and time histogram
    """
    df = pd.read_csv(imagelog_path)

    # Transform cell in the 'labels' column from str to list.  The actual
    # cell content is a list wrapped around quotes (eg. "['person',
    # 'dog']"). Transformating the data data gives us the labels in a
    # usable representation.
    labels_col = df['labels'].apply((lambda arr: ast.literal_eval(arr)))
    # Turn the columns into a lists
    labels_col = labels_col.to_list()
    timestamp_col = df['timestamp'].to_list()
    datetime_col = df['datetime'].to_list()

    # Create a dataframe that flattens each label into its own row with
    # its own timestamp and datetime.
    data = []

    for row_index in range(len(labels_col)):
        labels = labels_col[row_index]
        timestamp = timestamp_col[row_index]
        datetime_entry = datetime_col[row_index]
        for label in labels:
            # This is where the real flattening happens.  We flatten each
            # class in each label list.
            data += [[label, timestamp, datetime_entry]]

    flattened_df = pd.DataFrame(data,
                                columns=['label', 'timestamp', 'datetime'])

    return flattened_df
