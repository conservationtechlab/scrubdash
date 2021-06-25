import os
import asyncio
import struct
import pickle
from datetime import datetime


class asyncio_server:
    def __init__(
            self,
            queue,
            ip='127.0.0.1',
            port=8888,
            record_folder='saved_images/'):
        self.queue = queue
        self.ip = ip
        self.port = port
        self.RECORD_FOLDER = record_folder

    def save_image_to_disk(self, image, class_name):
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%dT%Hh%Mm%Ss.%f')[:-3]
        filename = '{}_{}.jpeg'.format(timestamp, class_name)
        filepath = os.path.join(self.RECORD_FOLDER, filename)

        # saving image to disk
        with open(filepath, 'wb') as saved_img:
            saved_img.write(image)

        # update csv log that stores all image records
        with open('image_log.csv', 'a') as image_csv:
            image_csv.write('{},{}\n'.format(filepath, class_name))

        return filepath

    # handles image socket messages
    async def handle_image(self, reader, writer):
        # read size of image bytestream
        image_struct = await reader.read(struct.calcsize('<L'))
        image_size = struct.unpack('<L', image_struct)[0]
        # for debugging: print(image_size)

        # read in image bytestream
        image = await reader.readexactly(image_size)

        # read size of lboxes struct
        lboxes_struct = await reader.read(struct.calcsize('<L'))
        lboxes_size = struct.unpack('<L', lboxes_struct)[0]

        # read in lboxes bytestream
        lboxes_bytes = await reader.readexactly(lboxes_size)
        lboxes = pickle.loads(lboxes_bytes)
        # for debugging: print(lboxes)
        # ex: [{'class_name': 'cheetah'}]
        class_name = lboxes[0]['class_name']

        # save image to disk and to the csv
        filename = self.save_image_to_disk(image, class_name)

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
    async def handle_echo(self, reader, writer):
        # read size of header bytestream
        header_struct = await reader.read(struct.calcsize('<L'))
        header_size = struct.unpack('<L', header_struct)[0]

        # read in header bytestream
        header_bytes = await reader.readexactly(header_size)
        header = header_bytes.decode()

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
        server = await asyncio.start_server(self.handle_echo, '127.0.0.1',
                                            8888)

        async with server:
            # the server will listen forever until we close it
            await server.serve_forever()

        server.close()

    def start_server(self):
        asyncio.run(self.run_forever())
