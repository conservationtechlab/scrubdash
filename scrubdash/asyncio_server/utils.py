import os
import pickle
import struct

import yaml


def get_subdirectories(parent_directory):
    all_subdirs = [os.path.join(parent_directory, d)
                   for d in os.listdir(parent_directory)
                   if os.path.isdir(os.path.join(parent_directory, d))]

    return all_subdirs


def get_most_recent_subdirectory(directory_list):
    latest_subdir = max(directory_list, key=os.path.getmtime)

    return latest_subdir


async def read_and_unserialize_socket_msg(reader):
    # Read size of msg bytestream
    msg_struct = await reader.read(struct.calcsize('<L'))
    msg_size = struct.unpack('<L', msg_struct)[0]

    # Read in msg bytestream
    msg_bytes = await reader.readexactly(msg_size)
    msg = pickle.loads(msg_bytes)

    return msg


def append_to_yaml(key, value, yaml_file, flow_style=False):
    pair = {key: value}
    yaml.dump(pair, yaml_file, default_flow_style=flow_style)
