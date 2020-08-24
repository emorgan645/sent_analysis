from threading import Thread

from flask_mail import Message

from app import app
from app import mail

"""
The send_async_email function runs in a background thread, invoked via the Thread() class in the last line of send_email(). 
"""


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()
