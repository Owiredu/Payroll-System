from PyQt5.QtCore import QThread, pyqtSignal
import smtplib
import sys
import os
import pickle
import mimetypes
from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid


class SendEmail(QThread):
    """
    This class sends an email notification
    """

    error_message = pyqtSignal(str)
    progress_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def create_smtp_connection(self):
        """
        This method creates the smtp connection
        """
        # create connection
        try:
            self.smtp = smtplib.SMTP('smtp.gmail.com', 587, 'localhost')
            self.smtp.ehlo()
            self.smtp.starttls()
            self.smtp.login(self.sender_email, self.sender_password)
        except:
            # if connection fails, try again
            self.smtp = smtplib.SMTP('smtp.gmail.com', 587, 'localhost')
            self.smtp.ehlo()
            self.smtp.starttls()
            self.smtp.login(self.sender_email, self.sender_password)

    def set_email_info(self, recipient_emails):
        # argument types: list
        """
        This method gets the email data
        """
        self.sender_email = "unibasesoftware@gmail.com"
        self.sender_password = "Godisgood2018"
        self.sender_name = 'Payroll System'
        self.recipient_emails = recipient_emails
        self.subject = 'Salary Payment'
        self.content = 'Your salary has been tranferred to your account. Thank you'

    def set_subject_sender_recipient(self):
        """
        This method set the subject, sender and recipient emails
        """
        # create the message holder
        self.message = EmailMessage()
        self.message['Subject'] = self.subject
        self.message['From'] = Address(self.sender_name, '', self.sender_email)
        self.message['To'] = self.recipient_emails.split(';')

    def set_msg_content(self):
        """
        This method sets the content of the email
        """
        self.message.set_content(self.content)

    def smtp_send_message(self):
        """
        This method sends the message
        """
        self.smtp.send_message(self.message)

    def run(self):
        """
        This method sends the alert
        """
        try:
            # send completion notification
            self.progress_message.emit("Sending Message(s) ...")
            # create connection to smtp server
            self.create_smtp_connection()
            try:
                self.set_subject_sender_recipient()
                self.set_msg_content()
                self.smtp_send_message()
                self.close_smtp()
                # send completion notification
                self.progress_message.emit("success")
            except:
                # send message dispatch error signal
                self.error_message.emit("dispatch_failure")
        except:
            # send connection failure error
            self.error_message.emit("connection_failure")

    def close_smtp(self):
        """
        This method closes the smtp server
        """
        self.smtp.quit()
