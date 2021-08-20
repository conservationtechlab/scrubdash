import ast
import base64
from datetime import datetime

import pandas as pd


# function to update image dictionary
def create_image_dict(class_list, image_log):
    """
    Updates the image dictionary used by the dash server

    Parameters
    ----------
    class_list : list of str
        The list of classes the scrubcam filters images for
    image_log : str
        The absolute path of the image log for the current user session

    Returns
    -------
    dict of { 'class_name' : str }
        An updated dictionary that maps the most recent image for each
        each class_name. The image is represented as the absolute path
        to the image
    """
    # create empty image dictionary
    image_dict = {}

    if not class_list:
        return image_dict

    # populate the image dictionary
    # initialize image path to most recent entry in image_log.csv
    df = pd.read_csv(image_log)

    for classification in class_list:
        # resets the indices after dropping rows
        filtered = df[df['labels'].str.contains(
            classification)].reset_index(drop=True)
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


# returns base64 encoding of image
def get_base64_image(filename):
    """
    Decodes a bytes-like image file into an ASCII string to be used as
    an HTML img source

    Parameters
    ----------
    filename : str
        The absolute path of the image file

    Returns
    -------
    str
        An ASCII decoding of the image bytes
    """
    base64_image = None
    if filename is None:
        return ""

    with open(filename, 'rb') as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('ascii')

    return base64_image


# TODO: rename method to get_total_duration or something
# source: https://stackoverflow.com/questions/1345827/how-do-i-find-the-time-difference-between-two-datetime-objects-in-python
# slightly modified from the source to return the total duration in a
# year, day, hour, minute, second format
def get_durations(then):

    # Returns a duration as specified by variable interval
    # Functions, except totalDuration, returns [quotient, remainder]
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
    durations = get_durations(then)
    styles = {'color': 'red', 'whiteSpace': 'pre-wrap'}

    print(durations)

    if durations['years'] > 0:
        msg = ('DISCONNECTED\nLast online: {} year(s), {} day(s) ago'
               .format(durations['years'], durations['days']))
    elif durations['days'] > 0:
        msg = ('DISCONNECTED\nLast online: {} day(s), {} hours(s) ago'
               .format(durations['days'], durations['hours']))
    elif durations['hours'] > 0:
        msg = ('DISCONNECTED\nLast online: {} hours(s), {} minute(s) ago'
               .format(durations['hours'], durations['minutes']))
    elif durations['minutes'] > 0:
        msg = ('DISCONNECTED\nLast online: {} minute(s), {} second(s) ago'
               .format(durations['minutes'], durations['seconds']))
    elif durations['seconds'] > 20:
        # check for 20 seconds instead of 15 seconds to allow for
        # a small amount of network latency
        msg = ('DISCONNECTED\nLast online: {} second(s) ago'
               .format(durations['seconds']))
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
