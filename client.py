#!/usr/bin/env python3

import asyncio
import pickle
import struct
import pandas as pd


"""
referenced from:
https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_client.py

To run with app_V2.py:
1. start app_V2.py first in a terminal
2. start client.py in another terminal
3. press 'enter' to send a message to the dash server or 'quit' to quit

You should see messages containing the image path and the class name appear on
the website page on localhost:8050

This client cycles through images in a csv and sends the image bystream, along
with metadata, to the asyncio server.
"""


class Client:
    def __init__(
            self,
            ip='127.0.0.1',
            port=8888,
            name='client',
            message_max_length=1e6):
        """
        127.0.0.1 is the localhost
        port could be any port
        """
        self.ip = ip
        self.port = port
        self.name = name
        self.message_max_length = int(message_max_length)
        """
        member variables for sending image path from csv
        """
        self.df = pd.read_csv('client.csv')
        self.parity = 0
        self.animal = 0
        self.row = 0
        self.image_path = self.df.iloc[self.row].values[0]
        self.image_bytes = None
        self.class_name = self.df.iloc[self.row].values[1]

    def update_img(self):
        # updating parity if animal == 1 (iterated through all animals)
        self.parity = 1 - self.parity if self.animal == 11 else self.parity
        # updating animal image to retrieve from csv
        self.animal = 0 if self.animal == 11 else self.animal + 1
        # updating row to retrieve
        self.row = (((self.animal) * 2) +
                    1) % 24 if self.parity else ((self.animal) * 2) % 24
        self.image_path = self.df.iloc[self.row].values[0]
        self.class_name = self.df.iloc[self.row].values[1]

    async def tcp_echo_client(self):
        """
        on client side send the image for echo
        """

        # opening socket
        reader, writer = await asyncio.open_connection(self.ip, self.port)

        # obtaining the image bytes
        with open(self.image_path, 'rb') as image_file:
            self.image_bytes = image_file.read()

        # send_image
        # for debugging: print(len(self.image_bytes))
        writer.write(struct.pack('<L', len(self.image_bytes)))
        await writer.drain()

        # sending image bytes first
        writer.write(self.image_bytes)
        await writer.drain()

        # lboxes is array of dictionaries
        lboxes = [{"class_name": self.class_name}]
        lboxes_bytes = pickle.dumps(lboxes)

        # send lboxes second
        # for debugging: print("lboxes len: ", len(lboxes_bytes))
        writer.write(struct.pack('<L', len(lboxes_bytes)))
        await writer.drain()
        writer.write(lboxes_bytes)
        await writer.drain()

        print('closing the socket')
        # The following lines closes the stream properly If there is any
        # warning, it's due to a bug o Python 3.8:
        # https://bugs.python.org/issue38529 Please ignore it
        writer.close()
        await writer.wait_closed()

        # # updating next image to send
        print('updating image')
        self.update_img()

    def run_until_quit(self):
        # start the loop
        while True:
            # collect the message to send
            message = input(
                "Enter any key to send a new image or enter 'quit' to exit: ")
            if message in [
                'quit',
                'exit',
                ':q',
                'exit;',
                'quit;',
                'exit()',
                    '(exit)']:
                break
            else:
                asyncio.run(self.tcp_echo_client())


if __name__ == '__main__':
    client = Client()  # using the default settings
    client.run_until_quit()
