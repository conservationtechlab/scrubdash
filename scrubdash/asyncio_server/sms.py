import logging
import re
from email.message import EmailMessage

import yaml
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


class sms_sender:
    def __init__(self, config_file):
        self.CONFIG_FILE = config_file

        with open(self.CONFIG_FILE) as f:
            configs = yaml.load(f, Loader=yaml.SafeLoader)

        # TODO: add try except on KeyError
        self.SENDER = configs['SENDER']
        self.SENDER_PASSWORD = configs['SENDER_PASSWORD']
        self.RECEIVERS = configs['SMS_RECEIVER']

    # source https://github.com/acamso/demos/blob/master/_email/send_txt_msg.py
    # pylint: disable=too-many-arguments
    async def send_sms(self, image_path, notify_classes):

        for receiver in self.RECEIVERS:
            num = receiver['num']
            carrier = receiver['carrier']

            to_email = CARRIER_MAP[carrier]

            # build message
            message = EmailMessage()
            message["From"] = self.SENDER
            message["To"] = f"{num}@{to_email}"
            message["Subject"] = 'New Scrubdash Image'
            msg = ('We received an image with the following detected classes: '
                   '{}').format(notify_classes)
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
