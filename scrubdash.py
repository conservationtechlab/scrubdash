#!/usr/bin/env python3

"""
This module contains the entry point for the CLI script and the PyPI
console script
"""

import argparse
import yaml
import logging
from multiprocessing import Process, Queue

from scrubdash.asyncio_server.asyncio_server import AsyncioServer
from scrubdash.dash_server.dash_server import start_dash

parser = argparse.ArgumentParser()
parser.add_argument('config_filename')
parser.add_argument('-c', '--continue', dest='cont', action='store_true')
args = parser.parse_args()
CONFIG_FILE = args.config_filename
CONTINUE_RUN = args.cont

logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] %(message)s (%(name)s)')
log = logging.getLogger('main')

with open(CONFIG_FILE) as f:
    configs = yaml.load(f, Loader=yaml.SafeLoader)


def main():
    asyncio_to_dash_queue = Queue()
    asyncio_server = AsyncioServer(configs,
                                   asyncio_to_dash_queue,
                                   CONTINUE_RUN)

    # Start the asyncio server in a different process
    asyncio = Process(target=asyncio_server.start_server)
    asyncio.start()

    # Start the dash server in a different process
    dash = Process(target=start_dash, args=(configs,
                                            asyncio_to_dash_queue))
    dash.start()

    try:
        asyncio.join()
        dash.join()
    except KeyboardInterrupt:
        # Wait for asyncio server and dash server to shut down
        while asyncio.is_alive() or dash.is_alive():
            pass
        log.info('Successfully shut down scrubdash.')


if __name__ == "__main__":
    main()
