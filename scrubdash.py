#!/usr/bin/env python3
import argparse
import yaml
import logging

from multiprocessing import Process, Queue
from scrubdash.dash_server.dash_server import start_dash
import scrubdash.asyncio_server.asyncio_server as a_s

parser = argparse.ArgumentParser()
parser.add_argument('config_filename')
parser.add_argument('-c', '--cont', dest='cont', action='store_true')
args = parser.parse_args()
print(args)
CONFIG_FILE = args.config_filename
CONTINUE_RUN = args.cont

logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] %(message)s (%(name)s)')
log = logging.getLogger('main')

with open(CONFIG_FILE) as f:
    configs = yaml.load(f, Loader=yaml.SafeLoader)

ASYNCIO_SERVER_IP = configs['ASYNCIO_SERVER_IP']
ASYNCIO_SERVER_PORT = configs['ASYNCIO_SERVER_PORT']
DASH_SERVER_IP = configs['DASH_SERVER_IP']
DASH_SERVER_PORT = configs['DASH_SERVER_PORT']
RECORD_FOLDER = configs['RECORD_FOLDER']


def main():
    q = Queue()
    log_queue = Queue()
    asyncio_server = a_s.asyncio_server(q,
                                        log_queue,
                                        ASYNCIO_SERVER_IP,
                                        ASYNCIO_SERVER_PORT,
                                        RECORD_FOLDER,
                                        CONTINUE_RUN,
                                        CONFIG_FILE)

    asyncio = Process(target=asyncio_server.start_server)
    asyncio.start()

    image_log = log_queue.get(block=True)
    filter_classes = log_queue.get(block=True)

    dash = Process(target=start_dash, args=(q,
                                            image_log,
                                            filter_classes,
                                            DASH_SERVER_IP,
                                            DASH_SERVER_PORT))

    dash.start()

    try:
        asyncio.join()
        dash.join()
    except KeyboardInterrupt:
        # waits for asyncio and dash to shut down
        while asyncio.is_alive() or dash.is_alive():
            pass
        log.info('Successfully shut down scrubdash.')


if __name__ == "__main__":
    main()
