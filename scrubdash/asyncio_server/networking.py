"""
This file contains methods related to networking and sockets that are
used by the asyncio_server package.
"""

import pickle
import struct


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
