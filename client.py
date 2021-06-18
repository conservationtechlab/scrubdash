#!/usr/bin/env python3

import asyncio

"""
referenced from: https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_client.py

To run with server_example.py:
1. start server_example.py first in a terminal
2. start client.py in another terminal
3. follow print-back instructions on client side until you quit

You should see messages print in the server_example.py terminal

To run with app_V2.py:
1. start app_V2.py first in a terminal
2. start client.py in another terminal
3. follow print-back instructions on client side until you quit

You should see messages appear on the website page on localhost:8050
"""

class Client:
    def __init__(self, ip='127.0.0.1', port=8888, name='client', message_max_length=1e6):
        """
        127.0.0.1 is the localhost
        port could be any port
        """
        self.ip = ip
        self.port = port
        self.name = name
        self.message_max_length = int(message_max_length)

    async def tcp_echo_client(self, message):
        """
        on client side send the message for echo
        """
        reader, writer = await asyncio.open_connection(self.ip, self.port)
        print(f'{self.name} send: {message!r}')
        writer.write(message.encode())

        print('close the socket')
        # The following lines closes the stream properly
        # If there is any warning, it's due to a bug o Python 3.8: https://bugs.python.org/issue38529
        # Please ignore it
        writer.close()

    def run_until_quit(self):
        # start the loop
        while True:
            # collect the message to send
            message = input("Please input the next message to send: ")
            if message in ['quit', 'exit', ':q', 'exit;', 'quit;', 'exit()', '(exit)']:
                break
            else:
                asyncio.run(self.tcp_echo_client(message))


if __name__ == '__main__':
    client = Client()  # using the default settings
    client.run_until_quit()