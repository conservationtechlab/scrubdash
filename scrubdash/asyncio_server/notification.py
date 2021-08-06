import logging
import ssl
import re
from email import encoders
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from smtplib import SMTP_SSL, SMTPResponseException

import aiosmtplib

log = logging.getLogger(__name__)

HOST = "smtp.gmail.com"
# https://kb.sandisk.com/app/answers/detail/a_id/17056/~/list-of-mobile-carrier-gateway-addresses
# https://www.gmass.co/blog/send-text-from-gmail/
CARRIER_MAP = {
    "verizon": "vtext.com",
    "tmobile": "tmomail.net",
    "sprint": "messaging.sprintpcs.com",
    "at&t": "txt.att.net",
    "boost": "smsmyboostmobile.com",
    "cricket": "sms.cricketwireless.net",
    "uscellular": "email.uscc.net",
}


class notification:
    """
    A class that represents a notification sender

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
                 sender,
                 sender_password,
                 email_receivers,
                 sms_receivers):
        self.SENDER = sender
        self.SENDER_PASSWORD = sender_password
        self.EMAIL_RECEIVERS = email_receivers
        self.SMS_RECEIVERS = sms_receivers

    def _get_datetime(self, image_path):
        """
        Parses the date and time from the image path

        Parameters
        ----------
        image_path : str
            The absolute path of the image

        Returns
        -------
        tuple of (str, str)
            The date in yyyy-mm-dd format and the time in HHhMMmSSs
            format. An example is (2021-08-06, 02h16m05s)
        """
        # get filename from path
        filename = image_path.split('/')[-1]
        # remove .xxx.jpeg filename ending
        filename = filename[:-9]
        # split the datetime on 'T'
        datetime = filename.split('T')

        date = datetime[0]
        time = datetime[1]

        return (date, time)

    async def send_sms(self, image_path, notify_classes):
        """
        Sends an SMS notification to receivers passed to initializer

        Parameters
        ----------
        image_path : str
            The absolute path of the image
        notify_classes : list of str
            The list of classes to alert the receiver of. This list will
            be put in the notification message.
        """
        date, time = self._get_datetime(image_path)

        for receiver in self.SMS_RECEIVERS:
            num = receiver['num']
            carrier = receiver['carrier']

            to_email = CARRIER_MAP[carrier]

            # build message
            message = EmailMessage()
            message["From"] = self.SENDER
            message["To"] = f"{num}@{to_email}"
            message["Subject"] = 'New Scrubdash Image'
            msg = ('At {} {}, we received an image with the following detected'
                   ' classes: {}').format(date, time, notify_classes)
            message.set_content(msg)

            with open(image_path, 'rb') as content_file:
                content = content_file.read()
                message.add_attachment(
                    content,
                    maintype='image',
                    subtype='jpeg',
                    filename='{}'.format(image_path.split('/')[-1])
                )

            # send
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

    def send_email(self, image_path, notify_classes):
        """
        Sends an email notification to receivers passed to initializer

        Parameters
        ----------
        image_path : str
            The absolute path of the image
        notify_classes : list of str
            The list of classes to alert the receiver of. This list will
            be put in the notification message.
        """
        port = 465  # For SSL
        smtp_server = "smtp.gmail.com"

        # create message
        message = MIMEMultipart()
        date, time = self._get_datetime(image_path)

        body = ('At {} {}, we received an image with the following detected'
                ' classes: {}').format(date, time, notify_classes)

        message['From'] = self.SENDER
        message['To'] = ", ".join(self.EMAIL_RECEIVERS)

        message['Subject'] = ('Scrubdash: New {} class instance detected'
                              .format(notify_classes))

        message.attach(MIMEText(body, 'plain'))

        context = ssl.create_default_context()

        # create attachment
        with open(image_path, 'rb') as image:
            image_name = image_path.split('/')[-1]
            # set attachment mime and file name, the image type is jpeg
            mime = MIMEBase('image', 'jpeg', filename=image_name)
            # add required header data:
            mime.add_header(
                'Content-Disposition',
                'attachment',
                filename=image_name)
            mime.add_header('X-Attachment-Id', '0')
            mime.add_header('Content-ID', '<0>')
            # read attachment file content into the MIMEBase object
            mime.set_payload(image.read())
            # encode with base64
            encoders.encode_base64(mime)
            # add MIMEBase object to MIMEMultipart object
            message.attach(mime)

        try:
            with SMTP_SSL(smtp_server, port, context=context) as server:
                server.login(self.SENDER, self.SENDER_PASSWORD)
                server.send_message(message)
        except SMTPResponseException:
            # raise KeyboardInterrupt again so asyncio can catch it
            # not raising the interrupt only causes SMTP to stop, not the
            # entire asyncio server.
            raise KeyboardInterrupt
