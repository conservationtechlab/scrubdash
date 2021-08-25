"""
This file contains methods related to images that are used by the
asyncio_server package.
"""

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
