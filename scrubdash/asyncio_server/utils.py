import os
import pickle
import struct

import yaml


def get_subdirectories(parent_directory):
    """
    Find all immediate subdirectories in a directory.

    Parameters
    ----------
    parent_directory : str
        The absolute path of a directory

    Returns
    -------
    all_subdirs : list of str
        A list containing the absolute paths of all immediate
        subdirectories.
    """
    all_subdirs = [os.path.join(parent_directory, d)
                   for d in os.listdir(parent_directory)
                   if os.path.isdir(os.path.join(parent_directory, d))]

    return all_subdirs


def get_most_recent_subdirectory(directory_list):
    """
    Find the most recently modified directory.

    Parameters
    ----------
    directory_list : list of str
        A list containing the absolute paths of directories.

    Returns
    -------
    latest_subdir : str
        The absolute path of the most recently modified directory.
    """
    latest_subdir = max(directory_list, key=os.path.getmtime)

    return latest_subdir


async def read_and_unserialize_socket_msg(reader):
    """
    Read and unserialize the message bytestream received from ScrubCam.

    Parameters
    ----------
    reader : asyncio.StreamReader
        A reader object that provides APIs to read data from the IO
        stream

    Returns
    -------
    msg : str or int or bool or list
        The object representation of the bytestream message. This could be
        a message header, timestamp, flag, lbox list, or filter class
        list.
    """
    # Read size of msg bytestream
    msg_struct = await reader.read(struct.calcsize('<L'))
    msg_size = struct.unpack('<L', msg_struct)[0]

    # Read in msg bytestream
    msg_bytes = await reader.readexactly(msg_size)
    msg = pickle.loads(msg_bytes)

    return msg


def append_to_yaml(key, value, yaml_file, flow_style=False):
    """
    Append data to a yaml file.

    Parameters
    ----------
    key : str
        The key for the key-value pair data.
    value : str or int or list or dict
        The value for the key-value pair data.
    yaml_file : file object
        An opened yaml file
    flow_style : {True, False, None}, default=False
        The yaml.dump parameter specifying how to style the serialized
        data in the file.
    """
    pair = {key: value}
    yaml.dump(pair, yaml_file, default_flow_style=flow_style)
