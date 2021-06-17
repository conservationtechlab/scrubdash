#!/usr/bin/env python3

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import base64
import pandas as pd
import asyncio
from threading import Thread
import time
import logging
import os 
from multiprocessing import Process
from queue import Queue


# ** global variables **
df = pd.read_csv('client.csv')
filename = 'client_imgs/elephant-1.jpg'
file = None
with open(filename, 'rb') as image_file:
    file = base64.b64encode(image_file.read()).decode('ascii')

# ** Async Part **
# reference: https://stackoverflow.com/questions/67206119/asyncio-run-dash-flask-server-with-another-coroutine-concurrently

async def update_img_src():
    i = 0
    parity = 0      # 0 parity is even, 1 parity is odd
    global stop_threads
    while not stop_threads:
        print("entered: ", str(i))
        #logging.info("Thread    : entered")
        row = (((i+1)*2)+1)%12 if parity else ((i+1)*2)%12
        global filename 
        filename = df.iloc[row].values[0]
        with open(filename, 'rb') as image_file:
            global file 
            file = base64.b64encode(image_file.read()).decode('ascii')
        await asyncio.sleep(1.5)
        print("after await: ", str(i))
        #logging.info("Thread    : after await")
        i = (i+1)%12
        #logging.info("Thread    : incremented")        
        print("just incremented")

def async_main_wrapper():
    """Not async Wrapper around update_img_src to run it as target function of Thread"""
    asyncio.run(update_img_src())

# *** Dash Part ***

app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.layout = html.Div([
    html.Img(id='img', src='data:image/png;base64,{}'.format(file)),
    dcc.Interval(
        id='interval-component',
        interval=2*1000, # in milliseconds
        n_intervals=0
    )
])

# change image callback
@app.callback(Output('img', 'src'),
            Input('interval-component', 'n_intervals'))
def change_img(n_clicks):
    # print(filename)
    return('data:image/png;base64,{}'.format(file))

def info(title):
    print(title)
    print('module name:', __name__)
    print('parent process:', os.getppid())
    print('process id:', os.getpid())


async def handle_echo(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    print("{}".format(message))


# reference https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_server.py
async def run_forever():
    server = await asyncio.start_server(handle_echo, '127.0.0.1', 8888)

    async with server:
        await server.serve_forever()

    server.close()

run = False

def check():
    print(run)
# reference: https://stackoverflow.com/questions/19790570/using-a-global-variable-with-a-thread
def server_run(threadname):
    info('main line')
    global run
    print(threadname + str(run))
    if not run:
        run = True
        print(threadname + str(run))
        asyncio.run(run_forever())

if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")
    try: 
        # run async stuff in another thread
        stop_threads = False
        th1 = Thread(target=server_run, args=("Thread-1",))
        th2 = Thread(target=server_run, args=("Thread-2",))
        th1.start()
        th2.start()

        # run Dash server
        app.run_server(debug=True)
        stop_threads = True
        th1.join()

    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Main (pid: {})  : all done".format(os.getpid()))


"""
line 103 is the problem line.
For some reason, on line 107, `app.run_server(debug=True)` runs main again, which ends up creating an extra server thread. The second server thread cannot connect to the same socket since it is already in use and we get an error. 

I've tried this with extensive other threads and `app.run_server()` seems to be the problem. This problem also occurs when doing multi-processing too.


Trace Details:
    = the first execution of main is fine
    - the ppid and pids are the same, as they should be and it prints out False, True, True
    - the second execution of main is bad because it also prints out False, True, True when it should be True, True, True since the global variable run was updated from the first execution of main. Since the second execution of main goes into the Line 106, we try to connect to the socket twice.
    - I tried using the global variable `run` as a lock but it didn't work for some reason? It works between threads as evidence in False, True, True but for some reason the variable resets when `app.run_server()` executes. Maybe it forks the program? I have no idea..

Trace Begins:

(scrub_env) kendrake@/mnt/c/Users/kayts/Documents/SDZWA Internship/scrubdash$ python3 client.py 
main line
module name: __main__
main line
module name: __main__
parent process: 8
parent process: 8
process id: 2182
process id: 2182
Thread-1False
Thread-1True
Thread-2True
Dash is running on http://127.0.0.1:8050/

20:07:03: Dash is running on http://127.0.0.1:8050/

 * Serving Flask app 'client' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
main line
main line
module name: __main__
module name: __main__
parent process: 2182
process id: 2193
Thread-1False
Thread-1True
parent process: 2182
process id: 2193
Thread-2True
Exception in thread Thread-1:
Traceback (most recent call last):
  File "/usr/lib/python3.9/threading.py", line 954, in _bootstrap_inner
    self.run()
  File "/usr/lib/python3.9/threading.py", line 892, in run
    self._target(*self._args, **self._kwargs)
  File "/mnt/c/Users/kayts/Documents/SDZWA Internship/scrubdash/client.py", line 106, in server_run
    asyncio.run(run_forever())
  File "/usr/lib/python3.9/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "/usr/lib/python3.9/asyncio/base_events.py", line 642, in run_until_complete
    return future.result()
  File "/mnt/c/Users/kayts/Documents/SDZWA Internship/scrubdash/client.py", line 87, in run_forever
    server = await asyncio.start_server(handle_echo, '127.0.0.1', 8888)
  File "/usr/lib/python3.9/asyncio/streams.py", line 94, in start_server
    return await loop.create_server(factory, host, port, **kwds)
  File "/usr/lib/python3.9/asyncio/base_events.py", line 1494, in create_server
    raise OSError(err.errno, 'error while attempting '
OSError: [Errno 98] error while attempting to bind on address ('127.0.0.1', 8888): address already in use

"""