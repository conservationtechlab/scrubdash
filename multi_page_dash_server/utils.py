import base64
import pandas as pd


# function to update image dictionary
def create_image_dict(class_list, image_log):
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
    base64_image = None
    if filename is None:
        return ""

    with open(filename, 'rb') as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('ascii')

    return base64_image
