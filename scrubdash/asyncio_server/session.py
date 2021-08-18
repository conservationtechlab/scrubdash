import os
import csv
import time
import pickle
import struct
import logging
from datetime import datetime

import yaml

log = logging.getLogger(__name__)


class session:
    def __init__(self,
                 hostname,
                 record_folder,
                 continue_run,
                 config_file,
                 dash_queue,
                 filter_classes,
                 notification_sender,
                 alert_classes,
                 cooldown_time,
                 timestamp):
        self.HOSTNAME = hostname
        self.RECORD_FOLDER = record_folder
        self.CONTINUE_RUN = continue_run
        self.CONFIG_FILE = config_file
        self.FILTER_CLASSES = filter_classes
        self.dash_queue = dash_queue
        self.notification = notification_sender
        self.ALERT_CLASSES = alert_classes
        self.COOLDOWN_TIME = cooldown_time

        # Configure session paths
        log.info(continue_run)
        if continue_run:
            self.cont_run_config()
            self.initialize_scrubdash()
        else:
            self.new_run_config()
            self.initialize_scrubdash()

        # Email and SMS control flow variables
        self.LAST_ALERT_TIME = None

        # Update heartbeat timestamp
        self._update_heartbeat_file(time)

    def _update_heartbeat_file(self, timestamp):
        with open(self.HEARTBEAT_PATH, 'w') as heartbeat_file:
            # record heartbeat timestamp
            heartbeat = {'HEARTBEAT': timestamp}
            yaml.dump(heartbeat, heartbeat_file, default_flow_style=False)

    def initialize_scrubdash(self):
        """
        Sends an initilization message to scrubdash that contains the
        hostname, filter class list, and the image log. This gives all
        the metadata the dash server needs to include the host to the
        cam page and the grid page.
        """
        # send hostname, filter class list, image log, and timestamp
        # to dash server
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

        # get current timestamp
        timestamp = time.time()

        # send image path and class name to dash server
        message = {
            'header': 'IMAGE',
            'hostname': self.HOSTNAME,
            'img_path': filename,
            'labels': detected_classes,
            'timestamp': timestamp
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

        # update heartbeat timestamp
        self._update_heartbeat_file(timestamp)

        log.info("Finished processing image")

    async def handle_heartbeat(self, reader, writer):
        # read size of lboxes struct
        timestamp_struct = await reader.read(struct.calcsize('<L'))
        timestamp_size = struct.unpack('<L', timestamp_struct)[0]

        # read in timestamp bytestream
        timestamp_bytes = await reader.readexactly(timestamp_size)
        # convert str timestamp to int
        timestamp_bytes = int(timestamp_bytes)

        # send hearbeat to dash server
        message = {
            'header': 'CONNECTION',
            'hostname': self.HOSTNAME,
            'timestamp': timestamp_bytes
        }
        self.dash_queue.put(message)

        # update heartbeat timestamp
        self._update_heartbeat_file(timestamp_bytes)

    def new_run_config(self):
        """
        Configures the session object for a new run (new session). The
        user session folder, image log, and summary file are created
        within the host folder.
        """
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%dT%Hh%Mm%Ss.%f')[:-3]
        session_foldername = timestamp
        session_path = os.path.join(self.RECORD_FOLDER,
                                    self.HOSTNAME,
                                    session_foldername)
        os.makedirs(session_path)

        self.SESSION_PATH = session_path

        # make summary yaml file
        summary_filename = '{}_summary.yaml'.format(timestamp)
        self.SUMMARY_PATH = os.path.join(self.SESSION_PATH, summary_filename)

        with open(self.SUMMARY_PATH, 'a') as summary:
            # record hostname
            hostname = {'HOSTNAME': self.HOSTNAME}
            yaml.dump(hostname, summary, default_flow_style=False)

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

        # add FILTER_CLASSES to summary
        with open(self.SUMMARY_PATH, 'a') as summary:
            setting = {"FILTER_CLASSES": self.FILTER_CLASSES}
            yaml.dump(setting, summary, default_flow_style=None)

        # create heartbeat timestamp yaml file
        heartbeat_filename = '{}_heartbeat.yaml'.format(timestamp)
        self.HEARTBEAT_PATH = os.path.join(self.SESSION_PATH,
                                           heartbeat_filename)

        with open(self.SUMMARY_PATH, 'a') as summary:
            # record hostname
            hostname = {'HOSTNAME': self.HOSTNAME}
            yaml.dump(hostname, summary, default_flow_style=False)

    def cont_run_config(self):
        """
        Configures the session object for a continuing run. The most
        recent user session folder, image log, and summary files are
        retrieved from the host folder.
        """
        # get most recent host session
        HOST_FOLDER = os.path.join(self.RECORD_FOLDER, self.HOSTNAME)
        all_subdirs = [os.path.join(HOST_FOLDER, d)
                       for d in os.listdir(HOST_FOLDER)
                       if os.path.isdir(os.path.join(HOST_FOLDER, d))]

        latest_subdir = max(all_subdirs, key=os.path.getmtime)
        self.SESSION_PATH = latest_subdir

        # get yaml summary file
        timestamp = latest_subdir.split('/')[-1]
        summary_filename = '{}_summary.yaml'.format(timestamp)
        self.SUMMARY_PATH = os.path.join(self.SESSION_PATH, summary_filename)

        with open(self.SUMMARY_PATH) as f:
            configs = yaml.load(f, Loader=yaml.SafeLoader)

        # get filter classes from summary file
        self.FILTER_CLASSES = configs['FILTER_CLASSES']

        # get the image_log filename from summary file
        self.IMAGE_LOG = configs['IMAGE_LOG']

        # get yaml hearbeat file
        heartbeat_filename = '{}_heartbeat.yaml'.format(timestamp)
        self.HEARTBEAT_PATH = os.path.join(self.SESSION_PATH,
                                           heartbeat_filename)
