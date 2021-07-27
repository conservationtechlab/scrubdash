import os
import asyncio
import struct
import pickle
from datetime import datetime
import logging
import csv
import yaml

log = logging.getLogger(__name__)


class asyncio_server:
    def __init__(
            self,
            queue,
            image_queue,
            ip,
            port,
            record_folder,
            continue_run,
            config_file):
        self.queue = queue
        self.ip = ip
        self.port = port
        self.RECORD_FOLDER = record_folder
        self.CONTINUE_RUN = continue_run
        self.CONFIG_FILE = config_file
        self.image_queue = image_queue

    def _write_boxes_file(self, timestamp, lboxes):
        filename = '{}.csv'.format(timestamp)
        full_filename = os.path.join(self.SESSION_PATH, filename)
        with open(full_filename, 'w') as f:
            self.csv_writer = csv.writer(f,
                                         delimiter=',',
                                         quotechar='"',
                                         quoting=csv.QUOTE_MINIMAL)
            for lbox in lboxes:
                self.csv_writer.writerow([lbox['class_name'],
                                          lbox['confidence'],
                                          *lbox['box']])
                log.info('Loggged {}'.format(lbox['class_name']))

        return full_filename

    def save_image_and_lboxes(self, image, detected_classes, lboxes):
        now = datetime.now()
        unix_timestamp = now.timestamp()
        dt_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        timestamp = now.strftime('%Y-%m-%dT%Hh%Mm%Ss.%f')[:-3]
        image_filename = '{}.jpeg'.format(timestamp)
        image_path = os.path.join(self.SESSION_PATH, image_filename)

        # saving image to disk
        with open(image_path, 'wb') as saved_img:
            saved_img.write(image)

        # saving lboxes to csv
        lboxes_path = self._write_boxes_file(timestamp, lboxes)

        # update csv log that stores all image records
        # will want to change this to csv_writer to match _write_boxes_file()
        with open(self.IMAGE_LOG, 'a') as image_log:
            image_log.write(
                '{},{},{},{},{}\n'.format(
                    image_path,
                    '\"{}\"'.format(detected_classes),
                    lboxes_path,
                    unix_timestamp,
                    dt_timestamp))

        return image_path

    # handles image socket messages
    async def handle_image(self, reader, writer):
        log.info("handling image")

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
        filename = self.save_image_and_lboxes(image, detected_classes, lboxes)

        # send image path and class name to dash server
        message = {
            "header": "IMAGE",
            "img_path": filename,
            "labels": detected_classes
        }
        self.queue.put(message)

    async def handle_classes(self, reader, writer):
        # read size of class list bytestream
        class_list_struct = await reader.read(struct.calcsize('<L'))
        class_list_size = struct.unpack('<L', class_list_struct)[0]
        # for debugging: print(class_list_size)

        # read in class_list bytestream
        class_list_bytes = await reader.readexactly(class_list_size)
        class_list = pickle.loads(class_list_bytes)

        self.FILTER_CLASSES = class_list

        with open(self.SUMMARY_PATH, 'a') as summary:
            # record user session
            setting = {"FILTER_CLASSES": class_list}
            yaml.dump(setting, summary, default_flow_style=None)

        # for debugging: print(class_list)
        # send class list to dash server
        message = {"header": "CLASSES", "class_list": class_list}
        self.queue.put(message)

    # reads in messages from client and delegates reading messages
    # based on header received
    async def handle_header(self, reader, writer):
        # read size of header bytestream
        header_struct = await reader.read(struct.calcsize('<L'))
        header_size = struct.unpack('<L', header_struct)[0]

        log.debug('header size: {}'.format(header_size))

        # read in header bytestream
        header_bytes = await reader.readexactly(header_size)
        header = header_bytes.decode()

        return header

    # abstracted handler to receive messages
    # assumes several mesages are sent over one connection
    async def recv_message(self, reader, writer):
        # while loop since scrubcam only uses one socket connection
        # so we need to use the same callback instance
        log.info('Connected to ScrubCam')
        while True:
            header = await self.handle_header(reader, writer)

            if header == 'CLASSES':
                await self.handle_classes(reader, writer)
            elif header == 'IMAGE':
                await self.handle_image(reader, writer)

    async def handle_session(self):
        message = {"header": "LOG", "image_log": self.IMAGE_LOG}
        self.queue.put(message)

    # reference:
    # https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_server.py
    # creates a server that listens on localhost at port 8888 for
    # incoming messages
    # all incoming messages are handled by handle_echo(reader, writer)
    async def run_forever(self):
        log.info('Server Started')
        await self.handle_session()
        log.info('Configuration finished')
        server = await asyncio.start_server(self.recv_message,
                                            self.ip,
                                            self.port)

        async with server:
            # the server will listen forever until we cancel recv_message()
            # cancelling recv_message() automatically closes the server ref:
            # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.Server.serve_forever
            await server.serve_forever()

    def newrun_config(self):
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

    def contrun_config(self):
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

        # may be redundancy we can delete
        # create image_log if not found in session folder
        if not os.path.isfile(self.IMAGE_LOG):
            # create image log since it's somehow not in the folder
            with open(self.IMAGE_LOG, 'a') as imagelog:
                header = ['path', 'labels', 'lboxes', 'timestamp', 'datetime']

                csv_writer = csv.writer(imagelog,
                                        delimiter=',',
                                        quotechar='"',
                                        quoting=csv.QUOTE_MINIMAL)
                csv_writer.writerow(header)

    def send_imagelog(self):
        self.image_queue.put(self.IMAGE_LOG)

    def send_classes(self):
        try:
            self.image_queue.put(self.FILTER_CLASSES)
        except AttributeError:
            # catch if scrubcam is not connected to scrubdash yet
            # send empty filter_class list for now and asyncio will send the
            # actual list when it connects to scrubdash.
            self.FILTER_CLASSES = None
            self.image_queue.put(self.FILTER_CLASSES)

    def configure_record(self):
        # check if record folder specified exists or not
        record_exists = os.path.isdir(self.RECORD_FOLDER)

        if not record_exists:
            os.mkdir(self.RECORD_FOLDER)

        if self.CONTINUE_RUN:
            self.contrun_config()
        else:
            self.newrun_config()

        self.send_imagelog()
        self.send_classes()

    def start_server(self):
        try:
            self.configure_record()
            asyncio.run(self.run_forever())
        except KeyboardInterrupt:
            # I think asyncio.run() gracefully cleans up all resources on
            # KeyboardInterrupt...not 100% sure though
            log.info('Successfully shut down asyncio server.')
