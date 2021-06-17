#!/usr/bin/env python3

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import os
import logging
import asyncio
import threading
from threading import Thread

"""
This program simulates how I would create a monolithic program.
The intent is that the dash server runs on the main thread, with the asyncio server that receives socket connections being run on a different thread.
The problem is that the dash server seems to create another thread when executing, which creates socket connection issues.

How to see the error:
  - First, I recommend running the main on lines 88-116 to see a working example of locking the server code between two threads.
  - Then you should run the main on lines 128-157 to see what I would like to simulate, and how this breaks the program.
  - A traceback of the errors I got are at the very bottom of the file.
"""

# *** Server Code (can ignore) ***

# reads in a message from a client and prints out the message received
async def handle_echo(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    print("{}".format(message))

# reference https://github.com/CS131-TA-team/UCLA_CS131_CodeHelp/blob/master/Python/echo_server.py
# creates a server that listens on localhost at port 8888 for incoming messages
# all incoming messages are handled by handle_echo(reader, writer)
async def run_forever():
    server = await asyncio.start_server(handle_echo, '127.0.0.1', 8888)

    async with server:
        # the server will listen forever until we close it
        await server.serve_forever()

    server.close()

# *** End of Server Code ***

# *** Function to start server ***

# this function acquires the shared lock before running the server
# since the lock is shared and never released, only one thread should be able to start the server at port 8888
def server_run(threadname, lock):
    # prints the running thread and the address and status of the lock 
    logging.info("Start of {} (pid: {}). Parent is (pid: {}). Lock status: {}".format(threadname, os.getpid(), os.getppid(), str(lock)))

    if not lock.locked():
      lock.acquire()

      # prints the running thread that acquired the lock and the address and status of the lock
      logging.info("{} (pid: {}) acquried {}".format(threadname, os.getpid(), str(lock)))
      
      # no code below asyncio.run() should be executed since asyncio.run(run_forever()) runs forever
      asyncio.run(run_forever())

      logging.info("This should never print since asncio.run() should run forever")

      # uncommenting the below lines does not change the bug behavior (which is odd)
      # lock.release()    
      # logging.info("{} released {}".format(threadname, str(lock)))
    
    else:
      # no-op if lock already acquired since this means the server is already running
      logging.info("{} (pid: {}) terminates since lock {} already acquired".format(threadname, os.getpid(),str(lock)))


# *** Start of Dash Part ***

app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.layout = html.Div("DASH LAYOUT")

# *** End of Dash Part ***

"""
Working example with two threads.

One thread will acquire the lock and start the server.
The second thread will see that the lock is already locked and will do a no-op and gracefully terminate
"""
if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    
    # creating the shared lock
    lock = threading.Lock()

    try: 
        # run async stuff in another thread

        # gives address and status of shared lock
        logging.info("Start of main (pid: {}). Parent is (pid: {}). Lock status: {}".format(os.getpid(), os.getppid(), str(lock)))

        # create two threads that both try to start the server
        th1 = Thread(target=server_run, args=("Thread-1", lock))
        th2 = Thread(target=server_run, args=("Thread-2", lock))

        # start both threads
        th1.start()
        th2.start()

        # app.run_server(debug=True)

        th1.join()
        th2.join()

    except KeyboardInterrupt:
        # used for previous debugging purposes. can ignore
        logging.info("Main (pid: {})  : all done".format(os.getpid()))

"""
Example that breaks when simulating a monolithic approach (have dash run on the main thread and have asyncio server run on a different thread).

For some reason, running the dash server causes another thread to start the server, which ends up creating an OS error since the port address is already in use. The fact that it circumvents my lock is alarming since this was my only workaround to this problem.

Interestingly, running this main with `th1.start()` commented out does not result in the dash server creating a second main, which leads me to believe the problem results from a combination of running other threads and running dash.

Difference from working example:
  - th2 (Thread-2) is no longer being created
  - instead, I start the dash server with `app.run_server(debug=True)`
  - It looks like the dash server run on an entirely different process or interpreter since the lock addresses between dash and th1 are different...this was not the case in the above code where I create two threads that share the lock.
"""
# if __name__ == '__main__':
#     format = "%(asctime)s: %(message)s"
#     logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    
#     # creating the shared lock
#     lock = threading.Lock()

#     try: 
#         # run async stuff in another thread

#         # gives address and status of shared lock
#         logging.info("Start of main (pid: {}). Parent is (pid: {}). Lock status: {}".format(os.getpid(), os.getppid(), str(lock)))

#         # create one thread that starts the server
#         th1 = Thread(target=server_run, args=("Thread-1", lock))
#         # th2 = Thread(target=server_run, args=("Thread-2", lock))

#         # start the server thread
#         th1.start()
#         # th2.start()

#         # run our dash website server
#         app.run_server(debug=True)

#         th1.join()
#         # th2.join()

#     except KeyboardInterrupt:
#         # used for previous debugging purposes. can ignore
#         logging.info("Main (pid: {})  : all done".format(os.getpid()))


"""
Problem:
    - It looks like when the dash server executes, main is somehow ran again, with a completely different lock and everything. This is evidenced on line 167 and 179. Line 127 is the first time main is run and line 179 is the second time. Additionally, the parent of the second main is the first main. I'm not sure if this is forking a child or multiprocessing or what since the locks are at different addresses (0x7ff8c148c840 vs. 0x7f84fb38c870).
    - Since the locks are no longer shared, this allows the second main to create a thread that tries to start the asyncio server again, which causes the "OS: address already in use" error.

Traceback:

11:57:45: Start of main (pid: 1958). Parent is (pid: 8). Lock status: <unlocked _thread.lock object at 0x7ff8c148c840>
11:57:45: Start of Thread-1 (pid: 1958). Parent is (pid: 8). Lock status: <unlocked _thread.lock object at 0x7ff8c148c840>
11:57:45: Thread-1 (pid: 1958) acquried <locked _thread.lock object at 0x7ff8c148c840>
Dash is running on http://127.0.0.1:8050/

11:57:45: Dash is running on http://127.0.0.1:8050/

 * Serving Flask app 'working_client' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
11:57:45: Start of main (pid: 1961). Parent is (pid: 1958). Lock status: <unlocked _thread.lock object at 0x7f84fb38c870>
11:57:45: Start of Thread-1 (pid: 1961). Parent is (pid: 1958). Lock status: <unlocked _thread.lock object at 0x7f84fb38c870>
11:57:45: Thread-1 (pid: 1961) acquried <locked _thread.lock object at 0x7f84fb38c870>
Exception in thread Thread-1:
Traceback (most recent call last):
  File "/usr/lib/python3.9/threading.py", line 954, in _bootstrap_inner
    self.run()
  File "/usr/lib/python3.9/threading.py", line 892, in run
    self._target(*self._args, **self._kwargs)
  File "/mnt/c/Users/kayts/Documents/SDZWA Internship/scrubdash/working_client.py", line 51, in server_run
    asyncio.run(run_forever())
  File "/usr/lib/python3.9/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "/usr/lib/python3.9/asyncio/base_events.py", line 642, in run_until_complete
    return future.result()
  File "/mnt/c/Users/kayts/Documents/SDZWA Internship/scrubdash/working_client.py", line 26, in run_forever
    server = await asyncio.start_server(handle_echo, '127.0.0.1', 8888)
  File "/usr/lib/python3.9/asyncio/streams.py", line 94, in start_server
    return await loop.create_server(factory, host, port, **kwds)
  File "/usr/lib/python3.9/asyncio/base_events.py", line 1494, in create_server
    raise OSError(err.errno, 'error while attempting '
OSError: [Errno 98] error while attempting to bind on address ('127.0.0.1', 8888): address already in use
"""