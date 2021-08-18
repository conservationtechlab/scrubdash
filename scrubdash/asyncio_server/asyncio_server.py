import os
import ast
import time
import pickle
import struct
import asyncio
import logging

import yaml

from scrubdash.asyncio_server.session import session
from scrubdash.asyncio_server.notification import notification

log = logging.getLogger(__name__)


class asyncio_server:
    """
    Asynchronous server that receives messages from `scrubcam` and
    persistently saves data (images and lboxes) to disk.

    ...

    Attributes
    ----------
    ip : str
        The IP address used to receive messages on
    port : int
        The port number used to receive messages on
    dash_queue : multiprocessing.Queue
        The shared queue that allows communication between the asyncio
        server and dash server
    RECORD FOLDER : str
        The folder location to save user sessions in
    CONTINUE_RUN : bool
        A flag used to signify a new user session
    CONFIG_FILE : str
        The file location of the configuration file
    ALERT_CLASSES : list of str
        The list of classes to send a notification for if observed in a
        received image
    COOLDOWN_TIME : int
        The number of seconds that must elapse before another
        notification can be sent
    LAST_ALERT_TIME : float or int
        The unix time for the most recently sent notification
    """
    def __init__(self,
                 dash_queue,
                 ip,
                 port,
                 record_folder,
                 continue_run,
                 config_file):
        """
        Parameters
        ----------
        dash_queue : multiprocessing.Queue
            The shared queue that allows communication between the
            asyncio server and dash server
        ip : str
            The IP address used to receive messages on
        port : int
            The port number used to receive messages on
        record_folder : str
            The folder location to save user sessions in
        continue_run : bool
            A flag used to signify a new user session
        config_file : str
            The file location of the configuration file
        """
        self.dash_queue = dash_queue
        self.ip = ip
        self.port = port
        self.RECORD_FOLDER = record_folder
        self.CONTINUE_RUN = continue_run
        self.CONFIG_FILE = config_file

        # Email and SMS notification member variables
        with open(self.CONFIG_FILE) as f:
            configs = yaml.load(f, Loader=yaml.SafeLoader)
        self.SENDER = configs['SENDER']
        self.SENDER_PASSWORD = configs['SENDER_PASSWORD']
        self.EMAIL_RECEIVERS = configs['EMAIL_RECEIVERS']
        self.SMS_RECEIVERS = configs['SMS_RECEIVERS']
        self.ALERT_CLASSES = configs['ALERT_CLASSES']
        self.COOLDOWN_TIME = configs['COOLDOWN_TIME']

    async def handle_header(self, reader, writer):
        """
        Reads the bytestream of the message header from ScrubCam.

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
        str
            The message header describing what the contents of the
            message are
        """
        # read size of header bytestream
        header_struct = await reader.read(struct.calcsize('<L'))
        header_size = struct.unpack('<L', header_struct)[0]

        # read in header bytestream
        header_bytes = await reader.readexactly(header_size)
        header = header_bytes.decode('utf-8')

        return header

    async def handle_session_config(self, reader, writer):
        """
        Reads the bytestream of the hostname from the connecting ScrubCam.

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
        str
            The hostname of the ScrubCam that just connected
        """

        header = await self.handle_header(reader, writer)

        while header != 'DONE':
            log.info(header)
            # read size of incoming bytestream
            bytes_struct = await reader.read(struct.calcsize('<L'))
            bytes_size = struct.unpack('<L', bytes_struct)[0]

            # read in incoming bytestream message
            msg_bytes = await reader.readexactly(bytes_size)

            if header != 'CLASSES' and header != 'ALERT_CLASSES':
                msg = msg_bytes.decode('utf-8')
            else:
                msg = pickle.loads(msg_bytes)

            log.info(msg)

            if header == 'HOSTNAME':
                hostname = msg
            elif header == 'CONTINUE_RUN':
                continue_run = ast.literal_eval(msg)
            elif header == 'CLASSES':
                filter_classes = msg

            header = await self.handle_header(reader, writer)
            timestamp = time.time()

        notification_sender = notification(self.SENDER,
                                           self.SENDER_PASSWORD,
                                           self.EMAIL_RECEIVERS,
                                           self.SMS_RECEIVERS)

        host_session = session(hostname,
                               self.RECORD_FOLDER,
                               continue_run,
                               self.CONFIG_FILE,
                               self.dash_queue,
                               filter_classes,
                               notification_sender,
                               self.ALERT_CLASSES,
                               self.COOLDOWN_TIME,
                               timestamp)

        return host_session

    async def _recv_message(self, reader, writer):
        # abstracted handler to receive messages
        # assumes several mesages are sent over one connection
        log.info('Connected to ScrubCam')

        # while loop since scrubcam only uses one socket connection
        # so we need to use the same callback instance
        while True:
            header = await self.handle_header(reader, writer)
            log.info('recv header')
            if header == 'CONFIG':
                host_session = await self.handle_session_config(reader, writer)
            # elif header == 'CLASSES':
            #     await host_session.handle_classes(reader, writer)
            elif header == 'IMAGE':
                await host_session.handle_image(reader, writer)
            elif header == 'CONNECTION':
                await host_session.handle_heartbeat(reader, writer)

    def continue_run(self):
        host_subdirs = [os.path.join(self.RECORD_FOLDER, d)
                        for d in os.listdir(self.RECORD_FOLDER)
                        if os.path.isdir(os.path.join(self.RECORD_FOLDER, d))]
        log.info('HOST SUBDIRS: {}'.format(host_subdirs))

        for host_subdir in host_subdirs:
            # get most recent session folder
            session_subdirs = [os.path.join(host_subdir, d)
                               for d in os.listdir(host_subdir)
                               if os.path.isdir(os.path.join(host_subdir, d))]
            latest_subdir = max(session_subdirs, key=os.path.getmtime)
            session_path = latest_subdir

            # get yaml summary file
            timestamp = latest_subdir.split('/')[-1]
            summary_filename = '{}_summary.yaml'.format(timestamp)
            summary_path = os.path.join(session_path, summary_filename)

            with open(summary_path) as f:
                configs = yaml.load(f, Loader=yaml.SafeLoader)

            # get hostname from summary file
            hostname = configs['HOSTNAME']

            # get filter classes from summary file
            filter_classes = configs['FILTER_CLASSES']

            # get the image_log filename
            imagelog_filename = '{}_imagelog.csv'.format(timestamp)
            image_log = os.path.join(session_path, imagelog_filename)

            # get the heartbeat filename
            heartbeat_filename = '{}_heartbeat.yaml'.format(timestamp)
            heartbeat_file = os.path.join(session_path, heartbeat_filename)

            # get the latest heartbeat timestamp
            with open(heartbeat_file) as f:
                configs = yaml.load(f, Loader=yaml.SafeLoader)

            timestamp = configs['HEARTBEAT']

            # send class list and image log to dash server
            message = {
                    'header': 'INITIALIZE',
                    'hostname': hostname,
                    'class_list': filter_classes,
                    'image_log': image_log,
                    'timestamp': timestamp
                }
            self.dash_queue.put(message)

    # reference:
    # https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_server.py
    # creates a server that listens on localhost at port 8888 for
    # incoming messages
    # all incoming messages are handled by handle_echo(reader, writer)
    async def run_forever(self):
        """
        The asyncio coroutine that starts accepting connections until
        cancelled.
        """
        log.info('Server Started')
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
        Configures all user session data and executes the asyncio
        coroutine that starts the event loop to receive messages from
        ScrubCam.
        """
        try:
            if self.CONTINUE_RUN:
                self.continue_run()
            log.info('Configuration finished')
            asyncio.run(self.run_forever())
        except KeyboardInterrupt:
            # I think asyncio.run() gracefully cleans up all resources on
            # KeyboardInterrupt...not 100% sure though
            log.info('Successfully shut down asyncio server.')
