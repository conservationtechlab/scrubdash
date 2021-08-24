"""This file contains a class for receiving messages from ScrubCam."""

import asyncio
import logging
import os
import time

import yaml

from scrubdash.asyncio_server.filesystem import (get_most_recent_subdirectory,
                                                 get_subdirectories)
from scrubdash.asyncio_server.networking import read_and_unserialize_socket_msg
from scrubdash.asyncio_server.notification import NotificationSender
from scrubdash.asyncio_server.session import HostSession

log = logging.getLogger(__name__)


class AsyncioServer:
    """
    Asynchronous server that receives messages from ScrubCam and
    configures the environments (folders and files) used to persistently
    save ScrubCam session metadata.

    This class is used in conjunction with the HostSession class. Each
    HostSession instance represents an active connection to a ScrubCam and
    the HostSession instance is responsible for persistently saving data
    (images and lboxes) received from ScrubCam to the disk. Since a
    HostSession class is unable to read socket messages from ScrubCam, the
    AsyncioServer class is responsible for reading socket messages and
    relaying the messages to the correct HostSession instance.

    The AsyncioServer can also send messages to the dash server, but only
    does so to send configuration data like a HostSession's hostname,
    filter class list, and image log.
    ...

    Attributes
    ----------
    ip : str
        The IP address used to receive socket messages on
    port : int
        The port number used to receive socket messages on
    dash_queue : multiprocessing.Queue
        A shared queue that allows communication between the asyncio server
        and dash server
    RECORD FOLDER : str
        The folder location that each ScrubCam's metadata is saved to
    CONTINUE_RUN : bool
        A flag used to signify a new user session
    configs : str
        The dictionary of configuration settings obtained from loading a
        yaml config file
    """
    def __init__(self,
                 configs,
                 dash_queue,
                 continue_run):
        """
        Parameters
        ----------
        dash_queue : multiprocessing.Queue
            The shared queue that allows for communication between the
            asyncio server and dash server
        continue_run : bool
            A flag used to signify a new user session
        configs : str
            The dictionary of configuration settings obtained from loading a
            yaml config file
        """
        self.configs = configs
        self.dash_queue = dash_queue
        self.CONTINUE_RUN = continue_run

        # Attributes from the configs dictionary
        self.ip = configs['ASYNCIO_SERVER_IP']
        self.port = configs['ASYNCIO_SERVER_PORT']
        self.RECORD_FOLDER = configs['RECORD_FOLDER']

    async def handle_session_config(self, reader, writer):
        """
        Create a new `HostSession` instance.

        Read messages from ScrubCam containing `HostSession` initialization
        data, which includes `hostname`, `continue_run`, and
        `filter_classes`. A new `NotificationSender` instance is created for
        the `HostSession` instance.

        Parameters
        ----------
        reader : asyncio.StreamReader
            A reader object that provides APIs to read data from the IO
            stream
        writer : asyncio.StreamWriter
            A writer object that provides APIs to write data to the IO
            stream

        Returns
        -------
        host_session : HostSession
            An initialized `HostSession` instance
        """
        header = await read_and_unserialize_socket_msg(reader)

        # Get most of the `HostSession` parameters from ScrubCam
        while header != 'DONE':
            msg = await read_and_unserialize_socket_msg(reader)

            if header == 'HOSTNAME':
                hostname = msg
            elif header == 'CONTINUE_RUN':
                continue_run = msg
            elif header == 'CLASSES':
                filter_classes = msg

            header = await read_and_unserialize_socket_msg(reader)

        # Get the rest of the `HostSession` parameters
        timestamp = time.time()
        notification_sender = NotificationSender(self.configs)

        host_session = HostSession(hostname,
                                   self.RECORD_FOLDER,
                                   continue_run,
                                   self.configs,
                                   self.dash_queue,
                                   filter_classes,
                                   notification_sender,
                                   timestamp)

        return host_session

    async def _recv_message(self, reader, writer):
        # Abstracted handler to receive messages
        log.info('New ScrubCam connection detected')

        # Use while loop since each ScrubCam only uses one socket
        # connection.  The same reader instance must be used to read all
        # messages sent by a ScrubCam.  The host_session instance is
        # initialized when a 'CONFIG' header is read.  This implicitly
        # assumes that a 'CONFIG' header will always be the first header
        # sent whenever a ScrubCam connects.
        while True:
            header = await read_and_unserialize_socket_msg(reader)

            if header == 'CONFIG':
                host_session = await self.handle_session_config(reader, writer)
            elif header == 'IMAGE':
                await host_session.handle_image(reader, writer)
            elif header == 'CONNECTION':
                await host_session.handle_heartbeat(reader, writer)

    def _continue_run(self):
        """
        Send an initialization message to the dash server for each ScrubCam
        host folder saved in `RECORD_FOLDER`.

        The initialization message contains metadata obtained from each
        ScrubCam host's most recent session folder. The most recent session
        folder is defined by the folder with the most recent modified time.
        """
        # Get the absolute path for each ScrubCam host folder
        host_folders = get_subdirectories(self.RECORD_FOLDER)

        for host_folder in host_folders:
            # Get the absolute paths of all session folders for a host
            session_folders = get_subdirectories(host_folder)
            # Get the absolute path for the most recent session folder
            most_recent_session = get_most_recent_subdirectory(session_folders)

            # Get the yaml summary file path
            timestamp = most_recent_session.split('/')[-1]
            summary_filename = '{}_summary.yaml'.format(timestamp)
            summary_file = os.path.join(most_recent_session, summary_filename)

            with open(summary_file) as f:
                summary_configs = yaml.load(f, Loader=yaml.SafeLoader)

            # Get the hostname from the summary file
            hostname = summary_configs['HOSTNAME']

            # Get the filter classes from the summary file
            filter_classes = summary_configs['FILTER_CLASSES']

            # Get the image log file path
            imagelog_filename = '{}_imagelog.csv'.format(timestamp)
            imagelog_file = os.path.join(most_recent_session,
                                         imagelog_filename)

            # Get the heartbeat timestamp yaml file
            heartbeat_filename = '{}_heartbeat.yaml'.format(timestamp)
            heartbeat_file = os.path.join(most_recent_session,
                                          heartbeat_filename)

            # Get the heartbeat timestamp
            with open(heartbeat_file) as f:
                heartbeat_configs = yaml.load(f, Loader=yaml.SafeLoader)

            timestamp = heartbeat_configs['HEARTBEAT']

            # Send filter classes list and image log to dash server
            message = {
                    'header': 'INITIALIZE',
                    'hostname': hostname,
                    'class_list': filter_classes,
                    'image_log': imagelog_file,
                    'timestamp': timestamp
                }

            self.dash_queue.put(message)

    async def run_forever(self):
        """
        Coroutine that starts accepting connections until cancelled.

        Notes
        -----
        Adapted from https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.Server.serve_forever.
        """
        log.info('Server started')
        server = await asyncio.start_server(self._recv_message,
                                            self.ip,
                                            self.port)

        async with server:
            # the server will listen forever until we cancel _recv_message()
            # cancelling _recv_message() automatically closes the server ref:
            # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.Server.serve_forever
            await server.serve_forever()

    def start_server(self):
        """
        Execute the asyncio coroutine that starts the event loop to
        receive messages from ScrubCams.

        If the `CONTINUE_RUN` attribute is `True`, an initialization
        message to the dash server is sent for each ScrubCam host folder
        in `RECORD_FOLDER`.
        """
        try:
            if self.CONTINUE_RUN:
                self._continue_run()
            asyncio.run(self.run_forever())
        except KeyboardInterrupt:
            # I think asyncio.run() gracefully cleans up all resources on
            # KeyboardInterrupt...not 100% sure though
            log.info('Successfully shut down asyncio server.')
