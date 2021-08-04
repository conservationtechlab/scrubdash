# scrubdash
Dashboard for organizing, visualizing, and analyzing images coming in from a [ScrubCam(s)](https://github.com/icr-ctl/scrubcam). The dashboard allows users to see the most recent image taken for each class on the home page, scroll through the history of each image taken for a certain class, and analyze images with histograms and time-series figures. Users may also observe the labeled boxes in each image by toggling a confidence slider. 

## How It Works
ScrubDash utilizes multiprocessing to spawn two servers -- an `asyncio` server and a `dash` server.

### Asyncio Server
The `asyncio` server uses the `asyncio` library to receive to receive images from a ScrubCam. Additional functionalities include creating the session folder to persistently save all images and metadata for the current user session and sending an SMS and email notification to the recipient(s) listed in the config file when an image is received. 

### Dash Server
The `dash` server uses the `dash` library to render the client-facing dashboard.

## Installation
```python3 -m pip install --index-url https://test.pypi.org/simple/ --no-deps scrubdash```

## Usage
The core program in the project is `scrubdash.py` which spawns the two server processes. It accepts a YAML configuration file as a command line argument. There is an example config file in `./cfgs/config.yaml.example`.

```
Usage:
    scrubdash [OPTIONS] <config_file>
    
Options:
    -h, --help      Output a usage message and exit
    -c, --cont      Continue the most recent session
```

Once ScrubDash is running, a ScrubCam can connect to it. If starting a new user session, ScrubDash will render a "waiting to connect to scrubcam..." page until a ScrubCam has been successfully connected. If continuing a previous session, ScrubDash will automatically display information from the previous session -- no connection to ScrubCam is required unless a ScrubCam was never connected in the previous session.

## Config File
The following values should be changed in the config file:
  1. `ASYNCIO_SERVER_IP`: this is the public IP of the device running the `asyncio` server. This is the IP address the asyncio server receives images on.
  2. `RECORD_FOLDER`: this is the absolute path specifying where to save the data for each user session.
  3. `ALERT_CLASSES`: the list of classes ScrubDash should send an SMS and email notification for when observed in an image.
  4. `SENDER`: the email that `smtplib` uses to send the SMS and email notifications. **NOTE: this email will not receive notifications unless also specified as a receiver in `EMAIL_RECEIVERS` or `SMS_RECEIVERS`.**
  5. `SENDER_PASSWORD`: an unencripted plaintext string used to login to the email specified in `SENDER`. We recommend having `SENDER` be a throwaway email used soley as a proxy sender.
  6. `EMAIL_RECEIVERS`: a list of emails that will receive notifications when a class in `ALERT_CLASSES` is observed.
  7. `SMS_RECEIVERS`: a list of dictionaries specifying the phone number and carrier for each recipient that will receive an SMS notification when a class in `ALERT_CLASSES` is observed. Look at the **Supported Phone Carriers** section to see valid carriers.

### Supported Phone Carrriers
An SMS notification is only possible if a recipient's phone number is listed in `SUPPORTED_CARRIERS`. The spelling of the provider must be **EXACTLY** the same as listed in `SUPPORTED_CARRIERS`.
```
SUPPORTED_CARRIERS = [
    "verizon",
    "tmobile",
    "sprint",
    "at&t",
    "boost",
    "cricket",
    "uscellular",
]
```

## Example
The dashboard is accessible at `http://[ASYNCIO_SERVER_IP]:[DASH_SERVER_PORT]`. If using the values in `./cfgs/config.yaml.example`, the dashboard is accessible at `http://132.249.242.104:8050`
```
$ scrubdash -c cfgs/config.yaml
[INFO] Server Started (scrubdash.asyncio_server.asyncio_server)
[INFO] Configuration finished (scrubdash.asyncio_server.asyncio_server)
Dash is running on http://0.0.0.0:8050/

[INFO] Dash is running on http://0.0.0.0:8050/
 (scrubdash.dash_server.app)
 * Serving Flask app 'scrubdash.dash_server.app' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
[WARNING]  * Running on all addresses.
   WARNING: This is a development server. Do not use it in a production deployment. (werkzeug)
[INFO]  * Running on http://172.22.126.191:8050/ (Press CTRL+C to quit) (werkzeug)
```

## How To View Saved Images
To view saved images, go to the folder specified at `RECORD_FOLDER` in your config file.

### User Sessions
Each execution of ScrubDash without the `-c, --cont` flag creates a new user session folder. This user session folder is timestamped to the first execution of the user session, which will be denoted as `user_session_timestamp`. It does not timestamp the folder to the time of the first image received. Every user session includes these two files:
  1. `[user_session_timestamp]_imagelog.csv`: a csv that records five metadata for each image received.
    1. `path`: the absolute path to the saved image
    2. `labels`: a list containing all the unique classes observed in the image in descending confidence order.
    3. `lboxes`: the absolute path to the csv that lists the lbox coordinates for each object observed in the image.
    4. `timestamp`: the unix timestamp representing the time the image was received by the `asyncio` server. This is used to create figures to analyze image data.
    5. `datetime`: a datetime representation of the unix timestamp with the representation `%Y-%m-%dT%Hh%Mm%Ss.%f` (eg. `2021-07-30 14:24:18`). This is used to create figures to analyze image data.
  2. `[user_session_timestamp]_summary.yaml`: a yaml that records metadata for the user session. It copies everything listed in the config file and also includes:
    1. `USER_SESSION`: the absoluste path to the user session folder.
    2. `IMAGE_LOG`: the absoluste path to the image log csv.
