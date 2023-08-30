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
@app.route('/receive_sms', methods=['POST'])
def receive_sms():
    from_number = request.form.get('From')  # Sender's phone number
    to_number = request.form.get('To')      # Receiver's Plivo number
    received_text = request.form.get('Text')
    
    # Log sender's phone number and received text
    app.logger.info(f'from_number: {from_number}, received_text: {received_text}')
    
    if received_text.strip().isdigit():
        # Get response from picklist and update database
        response, numbered_intents, numbered_intents_dict, language = get_response_picklist(int(received_text), from_number)
        write_to_db(from_number, received_text, '', '', language, '', '1', response, numbered_intents_dict)
        print(response,'\n',numbered_intents)
        return '', 200
    else:
        # Translate, classify intent, get response, and update database
        text_to_classify, translated_text, language = translate(received_text)
        intent, confidence = send_to_watson_assistant(text_to_classify)
        response, numbered_intents, numbered_intents_dict = get_response(text_to_classify, intent, confidence, language)
        write_to_db(from_number, received_text, translated_text, text_to_classify, language, intent, confidence, response, numbered_intents_dict)
        
    # Log additional information
    app.logger.info(f'from_number: {from_number}, received_text: {received_text}, translated_text: {translated_text}, text_to_classify: {text_to_classify}, language: {language}, intent: {intent}, confidence: {confidence}, response: {response}, numbered_intents: {numbered_intents}')
    return '', 200

if __name__ == '__main__':
    app.run(debug=True)
