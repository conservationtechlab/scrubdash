import yaml
import ssl
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from smtplib import SMTP_SSL, SMTPResponseException


class email_sender:
    def __init__(self, config_file):
        self.CONFIG_FILE = config_file

        with open(self.CONFIG_FILE) as f:
            configs = yaml.load(f, Loader=yaml.SafeLoader)

        # TODO: add try except on KeyError
        self.SENDER = configs['SENDER']
        self.SENDER_PASSWORD = configs['SENDER_PASSWORD']
        self.RECEIVER = configs['RECEIVER']

    def send_email(self, image_path, notify_classes):
        port = 465  # For SSL
        smtp_server = "smtp.gmail.com"

        # create message
        message = MIMEMultipart()

        body = ('We received an image with the following detected classes: {}'
                .format(notify_classes))

        message['From'] = self.SENDER
        message['To'] = self.RECEIVER

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
