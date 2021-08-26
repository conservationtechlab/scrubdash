"""This file contains a class for sending email and SMS notifications."""

import logging
import re
import ssl
from email import encoders
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPResponseException

import aiosmtplib

log = logging.getLogger(__name__)

HOST = "smtp.gmail.com"
# Exhaustive list of carriers: https://kb.sandisk.com/app/answers/detail/a_id/17056/~/list-of-mobile-carrier-gateway-addresses
CARRIER_MAP = {
    "verizon": "vtext.com",
    "tmobile": "tmomail.net",
    "sprint": "messaging.sprintpcs.com",
    "at&t": "txt.att.net",
    "boost": "smsmyboostmobile.com",
    "cricket": "sms.cricketwireless.net",
    "uscellular": "email.uscc.net",
}


class NotificationSender:
    """
    A class that represents a notification sender.
    ...
    Attributes
    ----------
    SENDER : str
        The email used to send out notifications
    SENDER_PASSWORD : str
        The password for the email used to send out notifications
    EMAIL_RECEIVERS : list of str
        The list of emails notifications will be sent to
    SMS_RECEIVERS: list of dict of { 'num' : int, 'carrier' : str }
        The list of dictionaries containing phone numbers and service
        carriers that notifications will be sent to
    """
    def __init__(self,
                 configs):
        self.SENDER = configs['SENDER']
        self.SENDER_PASSWORD = configs['SENDER_PASSWORD']
        self.EMAIL_RECEIVERS = configs['EMAIL_RECEIVERS']
        self.SMS_RECEIVERS = configs['SMS_RECEIVERS']

    def _get_datetime(self, image_path):
        """
        Parse the date and time from the image path.
        Parameters
        ----------
        image_path : str
            The absolute path of the image
        Returns
        -------
        tuple of (str, str)
            The date in yyyy-mm-dd format and the time in HHhMMmSSs
            format. An example is (2021-08-06, 02h16m05s).
        """
        # Get the filename from the image log path
        filename = image_path.split('/')[-1]
        # Remove .xxx.jpeg filename ending
        filename = filename[:-9]
        # Split the datetime on 'T'
        datetime = filename.split('T')

        date = datetime[0]
        time = datetime[1]

        return (date, time)

    async def send_sms(self, hostname, image_path, detected_alert_classes):
        """
        Send an SMS notification to receivers listed in the `SMS_RECEIVERS`
        attribute.
        Parameters
        ----------
        hostname: str
            The hostname of the ScrubCam that took the image
        image_path : str
            The absolute path of the image
        detected_alert_classes : list of str
            The list of classes to alert the receiver of. This list will be
            put in the notification message.
        Notes
        -----
        This was adapted from a post from acamso on April 2, 2021 to a
        github code thread here: https://gist.github.com/alexle/1294495/39d13f2d4a004a4620c8630d1412738022a4058f
        """
        date, time = self._get_datetime(image_path)

        for receiver in self.SMS_RECEIVERS:
            num = receiver['num']
            carrier = receiver['carrier']

            to_email = CARRIER_MAP[carrier]

            # Create message.
            message = EmailMessage()
            message["From"] = self.SENDER
            message["To"] = f"{num}@{to_email}"
            message["Subject"] = 'New Scrubdash Image from {}'.format(hostname)
            msg = ('At {} {}, we received an image from {} with the following'
                   ' detected classes: {}'
                   .format(date, time, hostname, detected_alert_classes))
            message.set_content(msg)

            with open(image_path, 'rb') as content_file:
                content = content_file.read()
                message.add_attachment(
                    content,
                    maintype='image',
                    subtype='jpeg',
                    filename='{}'.format(image_path.split('/')[-1])
                )

            # Send.
            send_kws = dict(
                            username=self.SENDER,
                            password=self.SENDER_PASSWORD,
                            hostname=HOST,
                            port=587,
                            start_tls=True
                        )
            res = await aiosmtplib.send(message, **send_kws)  # type: ignore
            msg = ("failed to send sms to {}".format(num)
                   if not re.search(r"\sOK\s", res[1])
                   else "succeeded to send sms to {}".format(num))
            log.info(msg)

    def send_email(self, hostname, image_path, detected_alert_classes):
        """
        Send an email notification to receivers listed in the
        `EMAIL_RECEIVERS` attribute.
        Parameters
        ----------
        hostname: str
            The hostname of the ScrubCam that took the image
        image_path : str
            The absolute path of the image
        detected_alert_classes : list of str
            The list of classes to alert the receiver of. This list will
            be put in the notification message.
        """
        port = 465  # For SSL
        smtp_server = "smtp.gmail.com"

        # Create message.
        message = MIMEMultipart()
        date, time = self._get_datetime(image_path)

        message['From'] = self.SENDER
        message['To'] = ", ".join(self.EMAIL_RECEIVERS)
        message['Subject'] = ('Scrubdash ({}): New {} class instance detected'
                              .format(hostname, detected_alert_classes))
        body = ('At {} {}, we received an image from {} with the following '
                'detected classes: {}'
                .format(date, time, hostname, detected_alert_classes))
        message.attach(MIMEText(body, 'plain'))

        context = ssl.create_default_context()

        # Create image attachment.
        with open(image_path, 'rb') as image:
            image_name = image_path.split('/')[-1]
            # Set attachment mime and file name, the image type is jpeg.
            mime = MIMEBase('image', 'jpeg', filename=image_name)
            # Add required header data.
            mime.add_header(
                'Content-Disposition',
                'attachment',
                filename=image_name)
            mime.add_header('X-Attachment-Id', '0')
            mime.add_header('Content-ID', '<0>')
            # Read attachment file content into the MIMEBase object.
            mime.set_payload(image.read())
            # Encode with base64.
            encoders.encode_base64(mime)
            # Add MIMEBase object to MIMEMultipart object.
            message.attach(mime)

        try:
            with SMTP_SSL(smtp_server, port, context=context) as server:
                server.login(self.SENDER, self.SENDER_PASSWORD)
                server.send_message(message)
        except SMTPResponseException:
            # Raise KeyboardInterrupt again so the asyncio server can catch
            # it. Not raising the interrupt again causes only SMTP to stop,
            # not the entire asyncio server. I suspect this is because SMTP
            # will crash, but the asyncio server will be fine since the
            # run_forever coroutine was never cancelled by an interrupt.
            raise KeyboardInterrupt
