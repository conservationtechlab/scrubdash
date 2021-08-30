"""This file contains a class that represents a connected ScrubCam session."""

import csv
import logging
import os
import struct
import time
from datetime import datetime

import yaml

from scrubdash.asyncio_server.filesystem import (append_to_yaml,
                                                 get_most_recent_subdirectory,
                                                 get_subdirectories)
from scrubdash.asyncio_server.networking import read_and_unserialize_socket_msg

log = logging.getLogger(__name__)


class HostSession:
    """
    A class that represents a connected session between a ScrubCam and an
    AsyncioServer instance.
    This class is to be used in conjunction with the AsyncioServer class.
    Since the HostSession class cannot read socket meessages from
    ScrubCam, an AsyncioServer instance is used as an intermediary to
    relay ScrubCam messages to a HostSession instance.
    The HostSession class is responsible for persistently saving data and
    metadata (images, lboxes) to a user session folder. This class is
    responsible for writing the summary file and updating the image log
    and heartbeat files.
    The HostSession class is responsible for sending in time messages to
    the dash server, such as received images and the heartbeat received
    from a ScrubCam.
    ...
    Attributes
    ----------
    HOSTNAME : str
        The hostname of the ScrubCam
    RECORD_FOLDER : str
        The folder location that each ScrubCam's metadata is saved to
    CONTINUE_RUN : bool
        A flag used to signify a new user session
    configs : dict
        The dictionary of configuration settings obtained from loading a
        yaml config file
    FILTER_CLASSES
        The list of classes ScrubCam takes an image of
    dash_queue : multiprocessing.Queue
        The shared queue that allows for communication between the
        asyncio server and dash server
    IMAGE_LOG : str
        The absolute path of the image log
    SUMMARY_PATH : str
        The absolute path of the summary yaml file
    SESSION_PATH : str
        The absolute path of the session folder
    HEARTBEAT_PATH : str
        The absolute path of the heartbeat yaml file
    notification_sender : NotificationSender
        An instance of the NotificationSender class that sends email
        and SMS notifications
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
                 hostname,
                 record_folder,
                 continue_run,
                 configs,
                 dash_queue,
                 filter_classes,
                 notification_sender,
                 timestamp):
        """
        Parameters
        ----------
        hostname : str
            The hostname of the ScrubCam
        record_folder : str
            The folder location that each ScrubCam's metadata is saved to
        continue_run : bool
            A flag used to signify a new user session
        configs : dict
            The dictionary of configuration settings obtained from loading a
            yaml config file
        dash_queue : multiprocessing.Queue
            The shared queue that allows for communication between the
            asyncio server and dash server
        filter_classes : list of str
            The list of classes ScrubCam takes an image of
        notification_sender : NotificationSender
            An instance of the NotificationSender class that sends email
            and SMS notifications
        timestamp : float
            The Unix time the HostSession is instantiated at
        """
        self.HOSTNAME = hostname
        self.RECORD_FOLDER = record_folder
        self.CONTINUE_RUN = continue_run
        self.configs = configs
        self.FILTER_CLASSES = filter_classes
        self.dash_queue = dash_queue
        self.notification_sender = notification_sender
        self.ALERT_CLASSES = configs['ALERT_CLASSES']
        self.COOLDOWN_TIME = configs['COOLDOWN_TIME']

        # Configure session paths.
        if continue_run:
            self.cont_run_config()
        else:
            self.new_run_config()

        # Send ScrubCam host metadata to the dash server.
        self.initialize_scrubdash()

        # Initialize smail and SMS control flow variable.
        self.LAST_ALERT_TIME = None

        # Update heartbeat timestamp.
        self._update_heartbeat_file(time)

    def _update_heartbeat_file(self, timestamp):
        # Write the timestamp to the heartbeat file.
        with open(self.HEARTBEAT_PATH, 'w') as heartbeat_file:
            heartbeat = {'HEARTBEAT': timestamp}
            yaml.dump(heartbeat, heartbeat_file, default_flow_style=False)

    def initialize_scrubdash(self):
        """
        Send an initilization message to the dash server that contains the
        hostname, filter classes list, and the image log.
        This sends all the metadata the dash server needs to add the host
        to the cam page and the grid page.
        """
        now = time.time()
        message = {
                'header': 'INITIALIZE',
                'hostname': self.HOSTNAME,
                'class_list': self.FILTER_CLASSES,
                'image_log': self.IMAGE_LOG,
                'timestamp': now
            }
        self.dash_queue.put(message)

    def _write_boxes_file(self, timestamp, lboxes):
        # Write the lboxes to a comma separated value file (.csv) and
        # return the path of the file.
        csv_filename = '{}.csv'.format(timestamp)
        csv_path = os.path.join(self.SESSION_PATH, csv_filename)
        with open(csv_path, 'w') as lboxes_csv:
            csv_writer = csv.writer(lboxes_csv,
                                    delimiter=',',
                                    quotechar='"',
                                    quoting=csv.QUOTE_MINIMAL)
            for lbox in lboxes:
                csv_writer.writerow([lbox['class_name'],
                                     lbox['confidence'],
                                     *lbox['box']])
                log.info('Loggged {}'.format(lbox['class_name']))

        return csv_path

    def _save_image_and_lboxes(self, image, detected_classes, lboxes):
        """
        Save the image to disk, write the lboxes to a csv file, and
        record image metadata to the image log.
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
        image_path : str
            The saved location of the image
        """
        now = datetime.now()
        unix_timestamp = now.timestamp()
        datetime_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        formatted_timestamp = now.strftime('%Y-%m-%dT%Hh%Mm%Ss.%f')[:-3]
        image_filename = '{}.jpeg'.format(formatted_timestamp)
        image_path = os.path.join(self.SESSION_PATH, image_filename)

        # Save image to disk.
        with open(image_path, 'wb') as image_file:
            image_file.write(image)

        # Save lboxes to a csv file.
        lboxes_path = self._write_boxes_file(formatted_timestamp, lboxes)

        # Update image log that stores all image records.
        with open(self.IMAGE_LOG, 'a') as image_log:
            csv_writer = csv.writer(image_log,
                                    delimiter=',',
                                    quotechar='"',
                                    quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow([image_path,
                                 detected_classes,
                                 lboxes_path,
                                 unix_timestamp,
                                 datetime_timestamp])

        return image_path

    async def _send_notification_if_alert_class_detected(self,
                                                         image_path,
                                                         detected_classes,
                                                         now):
        """
        Send an email and SMS notification if one of the classes detected
        in the image is in `ALERT_CLASSES`.
        This method is *not* referentially transparent. This method has an
        internal cooldown and will only send the email and SMS
        notification once every 60 seconds. The next email and SMS
        notification may only be sent once the internal cooldown elapses.
        If this method is called before the cooldown elapses, a no-op is
        performed.
        Parameters
        ----------
        image_path : str
            The absolute path to the image
        detected_classes : list of str
            The list of classes detected in the image
        now : int
            A timestamp indicating when the image was received
        """
        # Check if an alert class is detected.
        alert_set = set(self.ALERT_CLASSES)
        detected_set = set(detected_classes)
        detected_alert_classes = list(alert_set.intersection(detected_set))

        # Check if cooldown time has elapsed since most recent alert.
        if self.LAST_ALERT_TIME is None:
            # This is the first alert being sent.
            cooldown_elapsed = True
        else:
            # Check if cooldown time has elapsed.
            time_diff = now - self.LAST_ALERT_TIME

            if time_diff >= self.COOLDOWN_TIME:
                cooldown_elapsed = True
            else:
                cooldown_elapsed = False

        # Send email and SMS notification if alert classes are detected and
        # cooldown time has elapsed.
        if len(detected_alert_classes) > 0 and cooldown_elapsed:
            self.notification_sender.send_email(self.HOSTNAME,
                                                image_path,
                                                detected_alert_classes)
            await self.notification_sender.send_sms(self.HOSTNAME,
                                                    image_path,
                                                    detected_alert_classes)
            last_alert_time = time.time()
            self.LAST_ALERT_TIME = last_alert_time

    async def handle_image(self, reader, writer):
        """
        Read the bytestreams of the lboxes and of the image from ScrubCam
        and save them to disk.
        This method also sends the SMS and email notifications and sends
        the image to the dash server so it can be shown as the most recent
        image on the main grid.
        Parameters
        ----------
        reader : asyncio.StreamReader
            A reader object that provides APIs to read data from the IO
            stream
        writer : asyncio.StreamWriter
            A writer object that provides APIs to write data to the IO
            stream
        """
        lboxes = await read_and_unserialize_socket_msg(reader)

        detected_classes = [lbox['class_name'] for lbox in lboxes]
        # Preserve only the classes in self.FILTER_CLASSES.
        detected_classes = [class_name for class_name in detected_classes
                            if class_name in self.FILTER_CLASSES]
        # Remove duplicate class occurances and preserve ordering by
        # confidence descending.
        detected_classes = list(dict.fromkeys(detected_classes))

        # Read size of image bytestream.
        image_struct = await reader.read(struct.calcsize('<L'))
        image_size = struct.unpack('<L', image_struct)[0]

        # Read in image bytestream.
        image = await reader.readexactly(image_size)

        # Save image to disk and to the csv.
        image_path = self._save_image_and_lboxes(image,
                                                 detected_classes,
                                                 lboxes)

        # Get current timestamp.
        now = time.time()

        # Send image path and class name to dash server.
        message = {
            'header': 'IMAGE',
            'hostname': self.HOSTNAME,
            'img_path': image_path,
            'labels': detected_classes,
            'timestamp': now
        }
        self.dash_queue.put(message)

        # Send notification if an alert class is detected.
        await self._send_notification_if_alert_class_detected(image_path,
                                                              detected_classes,
                                                              now)
        # Update heartbeat timestamp.
        self._update_heartbeat_file(now)

        log.info("Finished processing image")

    async def handle_heartbeat(self, reader, writer):
        """
        Read the heartbeat bytestream from ScrubCam and send a 'CONNECTION'
        message to the dash server.
        This method also updates timestamp in the heartbeat yaml file.
        Parameters
        ----------
        reader : asyncio.StreamReader
            A reader object that provides APIs to read data from the IO
            stream
        writer : asyncio.StreamWriter
            A writer object that provides APIs to write data to the IO
            stream
        """
        # Get timestamp.
        timestamp = await read_and_unserialize_socket_msg(reader)

        # Send hearbeat to dash server.
        message = {
            'header': 'CONNECTION',
            'hostname': self.HOSTNAME,
            'timestamp': timestamp
        }
        self.dash_queue.put(message)

        # Update heartbeat timestamp.
        self._update_heartbeat_file(timestamp)

    def new_run_config(self):
        """
        Configure the session instance for a new run. A new user session
        folder, image log, summary file, and heartbeat file are created in
        the host folder.
        This method also creates the record folder and all intermediate
        directories at runtime if has not been created yet.
        """
        now = datetime.now()
        formatted_timestamp = now.strftime('%Y-%m-%dT%Hh%Mm%Ss.%f')[:-3]
        session_foldername = formatted_timestamp
        session_path = os.path.join(self.RECORD_FOLDER,
                                    self.HOSTNAME,
                                    session_foldername)
        # Create session folder.
        os.makedirs(session_path)

        self.SESSION_PATH = session_path

        # Make image log csv.
        imagelog_filename = '{}_imagelog.csv'.format(formatted_timestamp)
        self.IMAGE_LOG = os.path.join(self.SESSION_PATH, imagelog_filename)

        with open(self.IMAGE_LOG, 'a') as imagelog:
            header = ['path', 'labels', 'lboxes', 'timestamp', 'datetime']

            csv_writer = csv.writer(imagelog,
                                    delimiter=',',
                                    quotechar='"',
                                    quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(header)

        # Create heartbeat timestamp yaml file
        heartbeat_filename = '{}_heartbeat.yaml'.format(formatted_timestamp)
        self.HEARTBEAT_PATH = os.path.join(self.SESSION_PATH,
                                           heartbeat_filename)

        # Make summary yaml file.
        summary_filename = '{}_summary.yaml'.format(formatted_timestamp)
        self.SUMMARY_PATH = os.path.join(self.SESSION_PATH, summary_filename)

        # Add metadata to summary file.
        with open(self.SUMMARY_PATH, 'a') as summary:
            # Add hostname to summary.
            append_to_yaml('HOSTNAME', self.HOSTNAME, summary)
            # Add session path to summary.
            append_to_yaml('USER_SESSION', self.SESSION_PATH, summary)
            # Add filter classes to summary.
            append_to_yaml('FILTER_CLASSES',
                           self.FILTER_CLASSES,
                           summary,
                           None)
            # Add image log  to summary.
            append_to_yaml('IMAGE_LOG', self.IMAGE_LOG, summary)
            # Add heartbeat to summary.
            append_to_yaml('HEARTBEAT_PATH', self.HEARTBEAT_PATH, summary)

            # Add config settings to summary.
            summary.write('\n# CONFIG FILE SETTINGS\n')
            for key, value in self.configs.items():
                # value_is_list is for formatting the metadata in the yaml.
                if isinstance(value, list):
                    value_is_list = None
                else:
                    value_is_list = False
                append_to_yaml(key, value, summary, value_is_list)

    def cont_run_config(self):
        """
        Configure the session instance for a continuing run. The most
        recent user session folder, image log, summary file, and heartbeat
        file are retrieved from the host folder.
        """
        # Get the most recent host session.
        HOST_FOLDER = os.path.join(self.RECORD_FOLDER, self.HOSTNAME)
        all_subdirs = get_subdirectories(HOST_FOLDER)

        latest_subdir = get_most_recent_subdirectory(all_subdirs)
        self.SESSION_PATH = latest_subdir

        # Get the yaml summary file.
        formatted_timestamp = latest_subdir.split('/')[-1]
        summary_filename = '{}_summary.yaml'.format(formatted_timestamp)
        self.SUMMARY_PATH = os.path.join(self.SESSION_PATH, summary_filename)

        with open(self.SUMMARY_PATH) as f:
            configs = yaml.load(f, Loader=yaml.SafeLoader)

        # Get filter classes from the summary file.
        self.FILTER_CLASSES = configs['FILTER_CLASSES']

        # Get the image_log filename from summary file.
        self.IMAGE_LOG = configs['IMAGE_LOG']

        # Get the yaml hearbeat file.
        self.HEARTBEAT_PATH = configs['HEARTBEAT_PATH']
