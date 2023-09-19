from handlers import *
from app_functions import *
from flask import Flask, request
from langdetect import detect
from sqlalchemy import create_engine, text
from get_postgres_str import get_postgres_str
import logging
from logging.config import fileConfig
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask_mail import Mail
import os
import time

# Load logging configuration from the logging.cfg file
logging.config.fileConfig('logging.cfg')

app = Flask(__name__)

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('SMTP_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('SMTP_PASSWORD')

mail = Mail(app)

# Send emails for log levels equal to or above WARNING
email_handler = SMTPHandler(
    mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
    fromaddr='silvasstar.joshva@gmail.com',
    toaddrs=['joshva.silvasstar@clinicchat.com'],
    subject='App Error - Tepeyac Chatbot',
    credentials=(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']),
    secure=()
)
email_handler.setLevel(logging.WARNING)
email_handler.setFormatter(logging.Formatter('Subject: %(levelname)s - App Error\n\n%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(email_handler)

# Route to receive SMS
@app.route("/webhooks/inbound-message", methods=["POST"])
def inbound_message():
    from_number = request.get_json().get('msisdn')  # Sender's phone number
    to_number = request.get_json().get('to')      # Receiver's Plivo number
    received_text = request.get_json().get('text')
    # Log sender's phone number and received text
    app.logger.info(f'from_number: {from_number}, received_text: {received_text}')
    
    if received_text.strip().isdigit():
        app.logger.info(f'Received text is a number')
        # Get response from picklist and update database
        response, numbered_intents, numbered_intents_dict, language = get_response_picklist(int(received_text), from_number)
        write_to_db(from_number, received_text, '', '', language, '', '1', response, numbered_intents_dict)
        print(response,'\n',numbered_intents)
        message = remove_hyperlinks(response)
        send_sms(from_number, message)
        time.sleep(1)
        send_sms(from_number, remove_hyperlinks(numbered_intents))
        return '', 200
    else:
        app.logger.info(f'Received text is a text message.')
        # Translate, classify intent, get response, and update database
        text_to_classify, translated_text, language = translate(received_text)
        app.logger.info(f'Text translated!')
        intent, confidence = send_to_watson_assistant(text_to_classify)
        app.logger.info(f'Got response from watson assistant!')
        response, numbered_intents, numbered_intents_dict = get_response(text_to_classify, intent, confidence, language)
        app.logger.info(f'Got response from get_response!')
        write_to_db(from_number, received_text, translated_text, text_to_classify, language, intent, confidence, response, numbered_intents_dict)
        app.logger.info(f'Wrote to database!')
        message = remove_hyperlinks(response)
        send_sms(from_number, message)
        time.sleep(1)
        send_sms(from_number, remove_hyperlinks(numbered_intents))
        
    # Log additional information
    app.logger.info(f'from_number: {from_number}, received_text: {received_text}, translated_text: {translated_text}, text_to_classify: {text_to_classify}, language: {language}, intent: {intent}, confidence: {confidence}, response: {response}, numbered_intents: {numbered_intents}')
    return '', 200

if __name__ == '__main__':
    app.run(debug=True, port = 3000 )
