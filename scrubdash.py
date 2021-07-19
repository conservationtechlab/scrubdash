#!/usr/bin/env python3
import argparse
import yaml
import logging

from multiprocessing import Process, Queue
from asyncio_server import asyncio_server
from multi_page_dash_server.dash_server import start_dash

parser = argparse.ArgumentParser()
parser.add_argument('config_filename')
args = parser.parse_args()
CONFIG_FILE = args.config_filename

logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] %(message)s (%(name)s)')
log = logging.getLogger('main')

with open(CONFIG_FILE) as f:
    configs = yaml.load(f, Loader=yaml.SafeLoader)

ASYNCIO_SERVER_IP = configs['ASYNCIO_SERVER_IP']
ASYNCIO_SERVER_PORT = configs['ASYNCIO_SERVER_PORT']
DASH_SERVER_IP = configs['DASH_SERVER_IP']
DASH_SERVER_PORT = configs['DASH_SERVER_PORT']
RECORD_IMAGES_FOLDER = configs['RECORD_IMAGES_FOLDER']
RECORD_LBOXES_FOLDER = configs['RECORD_LBOXES_FOLDER']

log.info(configs)

if __name__ == '__main__':
    pass
    q = Queue()
    asyncio_server = asyncio_server(q,
                                    ASYNCIO_SERVER_IP,
                                    ASYNCIO_SERVER_PORT,
                                    RECORD_IMAGES_FOLDER,
                                    RECORD_LBOXES_FOLDER)
    asyncio = Process(target=asyncio_server.start_server)
    dash = Process(target=start_dash, args=(q,
                                            DASH_SERVER_IP,
                                            DASH_SERVER_PORT))
    asyncio.start()
    dash.start()

    try:
        asyncio.join()
        dash.join()
    except KeyboardInterrupt:
        # waits for asyncio and dash to shut down
        while asyncio.is_alive() or dash.is_alive():
            pass
        log.info('Successfully shut down scrubdash.')
