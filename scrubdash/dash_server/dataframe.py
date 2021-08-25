"""
This file contains methods related to pandas dataframes that are used
by the dash_server package.
"""

import ast

import pandas as pd


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
