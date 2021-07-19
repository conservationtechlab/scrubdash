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
            ip,
            port,
            record_folder,
            new_run,
            config_file):
        self.queue = queue
        self.ip = ip
        self.port = port
        self.RECORD_FOLDER = record_folder
        self.NEW_RUN = new_run
        self.CONFIG_FILE = config_file

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

    def save_image_and_lboxes(self, image, class_name, lboxes):
        now = datetime.now()
        unix_timestamp = now.timestamp()
        dt_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        timestamp = now.strftime('%Y-%m-%dT%Hh%Mm%Ss.%f')[:-3]
        image_filename = '{}_{}.jpeg'.format(timestamp, class_name)
        image_path = os.path.join(self.SESSION_PATH, image_filename)

        # saving image to disk
        with open(image_path, 'wb') as saved_img:
            saved_img.write(image)

        # saving lboxes to csv
        lboxes_path = self._write_boxes_file(timestamp, lboxes)

        # update csv log that stores all image records
        # will want to change this to csv_writer to match _write_boxes_file()
        with open(self.image_log, 'a') as image_log:
            image_log.write(
                '{},{},{},{},{}\n'.format(
                    image_path,
                    class_name,
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
        # ex: [{'class_name': 'cheetah'}]
        class_name = lboxes[0]['class_name']

        # read size of image bytestream
        image_struct = await reader.read(struct.calcsize('<L'))
        image_size = struct.unpack('<L', image_struct)[0]
        # for debugging: print(image_size)

        # read in image bytestream
        image = await reader.readexactly(image_size)

        # save image to disk and to the csv
        filename = self.save_image_and_lboxes(image, class_name, lboxes)

        # send image path and class name to dash server
        message = {
            "header": "IMAGE",
            "img_path": filename,
            "label": class_name}
        self.queue.put(message)

    async def handle_classes(self, reader, writer):
        # read size of class list bytestream
        class_list_struct = await reader.read(struct.calcsize('<L'))
        class_list_size = struct.unpack('<L', class_list_struct)[0]
        # for debugging: print(class_list_size)

        # read in class_list bytestream
        class_list_bytes = await reader.readexactly(class_list_size)
        class_list = pickle.loads(class_list_bytes)

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

    # reference:
    # https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_server.py
    # creates a server that listens on localhost at port 8888 for
    # incoming messages
    # all incoming messages are handled by handle_echo(reader, writer)
    async def run_forever(self):
        log.info('Server Started')
        server = await asyncio.start_server(self.recv_message,
                                            self.ip,
                                            self.port)

        async with server:
            # the server will listen forever until we cancel recv_message()
            # cancelling recv_message() automatically closes the server ref:
            # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.Server.serve_forever
            await server.serve_forever()

    def configure_record(self):
        # check if record folder specified exists or not
        record_exists = os.path.isdir(self.RECORD_FOLDER)

        if not record_exists:
            os.mkdir(self.RECORD_FOLDER)

        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%dT%Hh%Mm%Ss.%f')[:-3]
        session_foldername = timestamp
        session_path = os.path.join(self.RECORD_FOLDER, session_foldername)
        os.mkdir(session_path)

        self.SESSION_PATH = session_path

        # make summary text file
        summary_filename = '{}_summary.txt'.format(timestamp)
        summary_path = os.path.join(self.SESSION_PATH, summary_filename)

        with open(summary_path, 'a') as summary:
            for key, value in yaml.load(open(self.CONFIG_FILE)).items():
                summary.write('{}: {}\n'.format(key, value))

        # make image log csv
        imagelog_filename = '{}_imagelog.csv'.format(timestamp)
        imagelog_path = os.path.join(self.SESSION_PATH, imagelog_filename)

        with open(imagelog_path, 'a') as imagelog:
            header = ['path', 'label', 'lboxes', 'timestamp', 'datetime']

            csv_writer = csv.writer(imagelog,
                                    delimiter=',',
                                    quotechar='"',
                                    quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(header)

        self.image_log = imagelog_path

    def start_server(self):
        try:
            self.configure_record()
            asyncio.run(self.run_forever())
        except KeyboardInterrupt:
            # I think asyncio.run() gracefully cleans up all resources on
            # KeyboardInterrupt...not 100% sure though
            log.info('Successfully shut down asyncio server.')
