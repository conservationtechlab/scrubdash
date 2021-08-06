import os
import asyncio
import struct
import pickle
import logging
import csv
import time
from datetime import datetime

import yaml

from scrubdash.asyncio_server.notification import notification

log = logging.getLogger(__name__)


class asyncio_server:
    """
    Asynchronous server that receives messages from `scrubcam` and
    persistently saves data (images and lboxes) to disk.

    ...

    Attributes
    ----------
    dash_queue : multiprocessing.Queue
        The shared queue that allows communication between the asyncio
        server and dash server
    scrubdash_queue : multiprocessing.Queue
        The shared queue that allows communication between the asyncio
        server and its parent scrubdash process
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
                 scrubdash_queue,
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
        scrubdash_queue : multiprocessing.Queue
            The shared queue that allows communication between the
            asyncio server and its parent scrubdash process
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
        self.scrubdash_queue = scrubdash_queue
        self.ip = ip
        self.port = port
        self.RECORD_FOLDER = record_folder
        self.CONTINUE_RUN = continue_run
        self.CONFIG_FILE = config_file

        # Email and SMS control flow variables
        with open(self.CONFIG_FILE) as f:
            configs = yaml.load(f, Loader=yaml.SafeLoader)
        self.ALERT_CLASSES = configs['ALERT_CLASSES']
        self.COOLDOWN_TIME = configs['COOLDOWN_TIME']
        self.LAST_ALERT_TIME = None

        # Email and SMS notification member variables
        SENDER = configs['SENDER']
        SENDER_PASSWORD = configs['SENDER_PASSWORD']
        EMAIL_RECEIVERS = configs['EMAIL_RECEIVERS']
        SMS_RECEIVERS = configs['SMS_RECEIVERS']

        self.notification = notification(SENDER,
                                         SENDER_PASSWORD,
                                         EMAIL_RECEIVERS,
                                         SMS_RECEIVERS)

    def _write_boxes_file(self, timestamp, lboxes):
        # writes the lboxes to a comma separated value file (.csv) and
        # returns the path of the file
        filename = '{}.csv'.format(timestamp)
        full_filename = os.path.join(self.SESSION_PATH, filename)
        with open(full_filename, 'w') as lboxes_csv:
            csv_writer = csv.writer(lboxes_csv,
                                    delimiter=',',
                                    quotechar='"',
                                    quoting=csv.QUOTE_MINIMAL)
            for lbox in lboxes:
                csv_writer.writerow([lbox['class_name'],
                                     lbox['confidence'],
                                     *lbox['box']])
                log.info('Loggged {}'.format(lbox['class_name']))

        return full_filename

    def _save_image_and_lboxes(self, image, detected_classes, lboxes):
        """
        Saves the image to disk, writes the lboxes to a csv file, and
        records image metadata to the image log.

        Parameters
        ----------
        image : bytes
            The bytes object representation of an image
        detected_classes : list of str
            The list of classes detected in the image
        lboxes : list of dict of { 'class_id' : int,
                                   'confidence' : float,
                                   'box' : list of int,
                                   'class_name' : str }
            The list of lboxes for each object identified in the image

        Returns
        -------
        str
            The saved location of the image
        """
        now = datetime.now()
        unix_timestamp = now.timestamp()
        dt_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        timestamp = now.strftime('%Y-%m-%dT%Hh%Mm%Ss.%f')[:-3]
        image_filename = '{}.jpeg'.format(timestamp)
        image_path = os.path.join(self.SESSION_PATH, image_filename)

        # saves image to disk
        with open(image_path, 'wb') as image_file:
            image_file.write(image)

        # saves lboxes to a csv file
        lboxes_path = self._write_boxes_file(timestamp, lboxes)

        # update image log that stores all image records
        with open(self.IMAGE_LOG, 'a') as image_log:
            csv_writer = csv.writer(image_log,
                                    delimiter=',',
                                    quotechar='"',
                                    quoting=csv.QUOTE_MINIMAL)

            csv_writer.writerow([image_path,
                                 detected_classes,
                                 lboxes_path,
                                 unix_timestamp,
                                 dt_timestamp])

        return image_path

    # handles image socket messages
    async def handle_image(self, reader, writer):
        """
        Reads the bytestreams of the lboxes and of the image from
        ScrubCam and saves them to disk. This method also sends the SMS
        and email notifications and sends the image to ScrubDash so it
        can be shown as the most recent image on the main grid.

        Parameters
        ----------
        reader : asyncio.StreamReader
            A reader object that provides APIs to read data from the IO
            stream
        writer : asyncio.StreamWriter
            A writer object that provides APIs to write data to the IO
            stream
        """
        # read size of lboxes struct
        lboxes_struct = await reader.read(struct.calcsize('<L'))
        lboxes_size = struct.unpack('<L', lboxes_struct)[0]

        # read in lboxes bytestream
        lboxes_bytes = await reader.readexactly(lboxes_size)
        lboxes = pickle.loads(lboxes_bytes)
        log.debug('lboxes received: {}'.format(lboxes))

        detected_classes = [lbox['class_name'] for lbox in lboxes]
        # preserve only the classes in filter_classes
        detected_classes = [class_name for class_name in detected_classes
                            if class_name in self.FILTER_CLASSES]
        # preserve only unique classes and preserve ordering by confidence
        # descending.
        detected_classes = list(dict.fromkeys(detected_classes))

        # read size of image bytestream
        image_struct = await reader.read(struct.calcsize('<L'))
        image_size = struct.unpack('<L', image_struct)[0]
        # for debugging: print(image_size)

        # read in image bytestream
        image = await reader.readexactly(image_size)

        # save image to disk and to the csv
        filename = self._save_image_and_lboxes(image,
                                               detected_classes,
                                               lboxes)

        # send image path and class name to dash server
        message = {
            "header": "IMAGE",
            "img_path": filename,
            "labels": detected_classes
        }
        self.dash_queue.put(message)

        # check if an alert class is detected
        alert_set = set(self.ALERT_CLASSES)
        detected_set = set(detected_classes)
        notify_classes = alert_set.intersection(detected_set)

        # check if cooldown time has elapsed since most recent alert
        if self.LAST_ALERT_TIME is None:
            # This is the first alert being sent
            cooldown_elapsed = True
        else:
            # get current time and check if cooldown time has elapsed
            now = time.time()
            time_diff = now - self.LAST_ALERT_TIME

            if time_diff >= self.COOLDOWN_TIME:
                cooldown_elapsed = True
            else:
                cooldown_elapsed = False

        # send sms and email alert if alert classes are detected and cooldown
        # time has elapsed
        if len(notify_classes) > 0 and cooldown_elapsed:
            self.notification.send_email(filename, list(notify_classes))
            await self.notification.send_sms(filename, list(notify_classes))
            last_alert_time = time.time()
            self.LAST_ALERT_TIME = last_alert_time

        log.info("Finished processing image")

    async def handle_classes(self, reader, writer):
        """
        Reads the bytestream of the class list from ScrubCam and writes it
        to the summary yaml file if it is not already written. This method
        also sends class list to ScrubDash so it can initialize the main
        grid.

        Parameters
        ----------
        reader : asyncio.StreamReader
            A reader object that provides APIs to read data from the IO
            stream
        writer : asyncio.StreamWriter
            A writer object that provides APIs to write data to the IO
            stream
        """
        # read size of class list bytestream
        class_list_struct = await reader.read(struct.calcsize('<L'))
        class_list_size = struct.unpack('<L', class_list_struct)[0]
        # for debugging: print(class_list_size)

        # read in class_list bytestream
        class_list_bytes = await reader.readexactly(class_list_size)
        class_list = pickle.loads(class_list_bytes)

        self.FILTER_CLASSES = class_list

        # add FILTER_CLASSES if not in summary yaml
        summary_keys = yaml.load(open(self.SUMMARY_PATH),
                                 Loader=yaml.SafeLoader).keys()

        if 'FILTER_CLASSES' not in summary_keys:
            with open(self.SUMMARY_PATH, 'a') as summary:
                # add FILTER_CLASSES to summary
                setting = {"FILTER_CLASSES": class_list}
                yaml.dump(setting, summary, default_flow_style=None)

        # send class list to dash server
        message = {"header": "CLASSES", "class_list": class_list}
        self.dash_queue.put(message)

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
        header = header_bytes.decode()

        return header

    async def _recv_message(self, reader, writer):
        # abstracted handler to receive messages
        # assumes several mesages are sent over one connection
        log.info('Connected to ScrubCam')

        # while loop since scrubcam only uses one socket connection
        # so we need to use the same callback instance
        while True:
            header = await self.handle_header(reader, writer)

            if header == 'CLASSES':
                await self.handle_classes(reader, writer)
            elif header == 'IMAGE':
                await self.handle_image(reader, writer)

    # reference:
    # https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_server.py
    # creates a server that listens on localhost at port 8888 for
    # incoming messages
    # all incoming messages are handled by handle_echo(reader, writer)
    async def run_forever(self):
        """
        The asyncio coroutine that starts acceping connections until
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

    def new_run_config(self):
        """
        Configures the asyncio server for a new run (new session). The
        user session folder, image log, and summary file are created.
        """
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%dT%Hh%Mm%Ss.%f')[:-3]
        session_foldername = timestamp
        session_path = os.path.join(self.RECORD_FOLDER, session_foldername)
        os.mkdir(session_path)

        self.SESSION_PATH = session_path

        # make summary yaml file
        summary_filename = '{}_summary.yaml'.format(timestamp)
        self.SUMMARY_PATH = os.path.join(self.SESSION_PATH, summary_filename)

        with open(self.SUMMARY_PATH, 'a') as summary:
            # record user session
            setting = {'USER_SESSION': self.SESSION_PATH}
            yaml.dump(setting, summary, default_flow_style=False)

            # record config settings
            for key, value in yaml.load(open(self.CONFIG_FILE),
                                        Loader=yaml.SafeLoader).items():
                setting = {key: value}
                yaml.dump(setting, summary, default_flow_style=False)

        # make image log csv
        imagelog_filename = '{}_imagelog.csv'.format(timestamp)
        self.IMAGE_LOG = os.path.join(self.SESSION_PATH, imagelog_filename)

        with open(self.IMAGE_LOG, 'a') as imagelog:
            header = ['path', 'labels', 'lboxes', 'timestamp', 'datetime']

            csv_writer = csv.writer(imagelog,
                                    delimiter=',',
                                    quotechar='"',
                                    quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(header)

        with open(self.SUMMARY_PATH, 'a') as summary:
            # record image log
            setting = {'IMAGE_LOG': self.IMAGE_LOG}
            yaml.dump(setting, summary, default_flow_style=False)

    def cont_run_config(self):
        """
        Configures the asyncio server for a continuing run. The most
        recent user session folder, image log, and summary files are
        retrieved.
        """
        all_subdirs = [os.path.join(self.RECORD_FOLDER, d)
                       for d in os.listdir(self.RECORD_FOLDER)
                       if os.path.isdir(os.path.join(self.RECORD_FOLDER, d))]

        latest_subdir = max(all_subdirs, key=os.path.getmtime)

        self.SESSION_PATH = latest_subdir

        # get filter_classes from yaml summary
        timestamp = latest_subdir.split('/')[-1]
        summary_filename = '{}_summary.yaml'.format(timestamp)
        self.SUMMARY_PATH = os.path.join(self.SESSION_PATH, summary_filename)

        with open(self.SUMMARY_PATH) as f:
            configs = yaml.load(f, Loader=yaml.SafeLoader)

        try:
            self.FILTER_CLASSES = configs['FILTER_CLASSES']
        except KeyError:
            self.FILTER_CLASSES = None

        # get the image_log filename
        imagelog_filename = '{}_imagelog.csv'.format(timestamp)
        self.IMAGE_LOG = os.path.join(self.SESSION_PATH, imagelog_filename)

    def send_imagelog(self):
        """
        Sends the image log path to ScrubDash.
        """
        self.scrubdash_queue.put(self.IMAGE_LOG)

    def send_classes(self):
        """
        Sends the class list to ScrubDash.
        """
        try:
            self.scrubdash_queue.put(self.FILTER_CLASSES)
        except AttributeError:
            # catch if scrubcam is not connected to scrubdash yet
            # send empty filter_class list for now and asyncio will send the
            # actual list when it connects to scrubdash.
            self.FILTER_CLASSES = None
            self.scrubdash_queue.put(self.FILTER_CLASSES)

    def configure_record(self):
        """
        Wrapper method that configures user session data and sends the
        image log path and class list to ScrubDash.
        """
        # check if record folder specified exists or not
        record_exists = os.path.isdir(self.RECORD_FOLDER)

        if not record_exists:
            os.mkdir(self.RECORD_FOLDER)

        if self.CONTINUE_RUN:
            self.cont_run_config()
        else:
            self.new_run_config()

        self.send_imagelog()
        self.send_classes()

    def start_server(self):
        """
        Configures all user session data and executes the asyncio
        coroutine that starts the event loop to receive messages from
        ScrubCam.
        """
        try:
            self.configure_record()
            log.info('Configuration finished')
            asyncio.run(self.run_forever())
        except KeyboardInterrupt:
            # I think asyncio.run() gracefully cleans up all resources on
            # KeyboardInterrupt...not 100% sure though
            log.info('Successfully shut down asyncio server.')
