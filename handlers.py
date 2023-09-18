
from dotenv import load_dotenv
import os
import requests
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import psycopg2
import vonage
from ibm_watson import LanguageTranslatorV3
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import re
from langdetect import detect
load_dotenv()
import logging
from sqlalchemy import create_engine, text
from get_postgres_str import get_postgres_str
from flask import current_app
import json

from fuzzywuzzy import fuzz



# PLIVO_AUTH_ID = os.getenv('PLIVO_AUTH_ID')
# PLIVO_AUTH_TOKEN = os.getenv('PLIVO_AUTH_TOKEN')

## Postgres username, password, and database name
postgres_str = get_postgres_str()
## Create the Connection
engine = create_engine(postgres_str, echo=False)

VONAGE_KEY=os.environ.get('VONAGE_KEY', None)
VONAGE_SECRET=os.environ.get('VONAGE_SECRET', None)
VONAGE_NUMBER=os.environ.get('VONAGE_NUMBER', None)

def splitter(message):
    tb = message.encode('utf-8')
    if len(tb) < 800:
        return [message]
    else:
        rgx = re.compile(b"[\s\S]*\W")
        m = rgx.match(tb[:1200])
        return [tb[:len(m[0])].decode('utf-8')] + splitter(tb[len(m[0]):].decode('utf-8'))

client = vonage.Client(key=VONAGE_KEY, secret=VONAGE_SECRET)
sms = vonage.Sms(client)

def send_sms(from_number, message):
    print(from_number, message)
    current_app.logger.info("Received message from app.py to handler before splitter")
    for message in splitter(message):
        responseData = sms.send_message({"from": VONAGE_NUMBER, "to": from_number,"text": message,})
        print(responseData)
        if responseData["messages"][0]["status"] == "0":
            current_app.logger.info("Message sent successfully.")
        else:
            current_app.logger.error(f"Message failed with error: {responseData['messages'][0]['error-text']}")



WATSON_API_KEY = os.getenv('WATSON_API_KEY')
WATSON_ASSISTANT_ID = os.getenv('WATSON_ASSISTANT_ID')
WATSON_URL = f'https://api.us-south.assistant.watson.cloud.ibm.com/v2/assistants/{WATSON_ASSISTANT_ID}/sessions'

authenticator = IAMAuthenticator(WATSON_API_KEY)
assistant = AssistantV2(
    version='2021-06-14',
    authenticator=authenticator
)
assistant.set_service_url(f'https://api.us-south.assistant.watson.cloud.ibm.com')


def send_to_watson_assistant(text):
    """
    Send a text to IBM Watson Assistant and get intent and confidence.

    This function sends a text input to IBM Watson Assistant and retrieves the detected
    intent along with its confidence score. If no intent is detected, it sets the intent
    as 'None' and the confidence as 0.

    Args:
        text (str): The text to be sent to Watson Assistant for intent recognition.

    Returns:
        tuple: A tuple containing the detected intent (str) and its confidence score (float).

    Example:
        intent, confidence = send_to_watson_assistant('How's the weather today?')
    """
    message_input = {
        'message_type:': 'text',
        'text': text
    }
    try:
        result = assistant.message_stateless(WATSON_ASSISTANT_ID, input=message_input).result['output']['intents'][0]
        intent = result['intent']
        confidence = result['confidence']
    except:
        intent = 'None'
        confidence = 0
    return intent, confidence


# Load IBM Language Translator API key and service URL from environment variables
api_key = os.getenv('IBM_LANGUAGE_TRANSLATOR_API')
service_url = os.getenv('IBM_LANGUAGE_TRANSLATOR_URL')

# Create an authenticator using the API key
authenticator = IAMAuthenticator(api_key)

# Create an instance of the LanguageTranslatorV3 class with specified version and authenticator
language_translator = LanguageTranslatorV3(
    version='2018-05-01',
    authenticator=authenticator
)

# Set the service URL for the language translator
language_translator.set_service_url(service_url)

def translate(text):
    """
    Translate text using IBM Language Translator API.

    This function detects the language of the input text and translates it to English
    using the IBM Language Translator API. If the detected language is already English,
    the original text is returned.

    Args:
        text (str): The text to be translated.

    Returns:
        tuple: A tuple containing the translated text (str), the source language (str),
        and the detected language (str).

    Example:
        translated_text, source_language, detected_language = translate('Hola, cómo estás?')
    """
    # Detect the language of the input text
    language_detection = language_translator.identify(text).get_result()
    language = language_detection['languages'][0]['language']
    print(language)
    translated_text = None
    
    if language != 'en':
        # Translate the text from the detected language to English
        translation = language_translator.translate(
            text=text,
            source=language,
            target='en'
        ).get_result()
        
        # Extract the translated text from the API response
        translated_text = translation['translations'][0]['translation']
        text_to_classify = translated_text
    else:
        # If the language is already English, use the original text
        text_to_classify = text
    
    return text_to_classify, translated_text, language


def write_to_db(from_number, received_text, translated_text, text_to_classify, language, intent, confidence, response, numbered_intents):
    """
    Write message details to the database.

    This function inserts the provided message details into the 'public.message' table
    in the database. The message details include sender's phone number, received text,
    translated text, text to classify, language, intent, confidence, response, and
    numbered intents.

    Args:
        from_number (str): Sender's phone number.
        received_text (str): Received text message.
        translated_text (str): Translated text (if applicable).
        text_to_classify (str): Text to be classified.
        language (str): Detected language of the text.
        intent (str): Detected intent of the text.
        confidence (float): Confidence score of the detected intent.
        response (str): Response generated for the text.
        numbered_intents (dict): Dictionary containing numbered intents.

    Returns:
        None
    """
    # Convert numbered_intents dictionary to JSON string
    numbered_intents = json.dumps(numbered_intents)
    
    # SQL query to insert data into the 'public.message' table
    query = '''
    INSERT INTO public.message(
        from_number, received_text, translated_text, text_to_classify, language, intent, confidence, response, numbered_intents)
    VALUES (
        :from_number, :received_text, :translated_text, :text_to_classify, :language, :intent, :confidence, :response, :numbered_intents
    )
    '''

    # Parameters to bind to the query
    params = {
        'from_number': from_number,
        'received_text': received_text,
        'translated_text': translated_text,
        'text_to_classify': text_to_classify,
        'language': language, 
        'intent': intent,
        'confidence': confidence,
        'response': response,
        'numbered_intents': numbered_intents
    }
    
    # Create a database engine and connect to it
    engine = create_engine(postgres_str, echo=False)
    conn = engine.connect()
    # Begin a transaction
    trans = conn.begin()

    try:
        # Create a parameterized query using text() and bind the parameters
        stmt = text(query).bindparams(**params)
    
        # Execute the query
        conn.execute(stmt)
    
        # Commit the transaction
        trans.commit()
    
    except Exception as e:
        # If an exception occurs, roll back the transaction
        trans.rollback()
        raise e
    
    finally:
        # Close the database connection
        conn.close()


def get_last_response(from_number):
    """
    Retrieve the last response details from the database.

    This function queries the 'public.message' table to retrieve the language and
    numbered intents of the last response sent from the specified phone number.

    Args:
        from_number (str): Sender's phone number.

    Returns:
        tuple: A tuple containing the language (str) and numbered intents (str)
        of the last response.

    Example:
        language, numbered_intents = get_last_response('+1234567890')
    """
    # SQL query to retrieve language and numbered_intents from the last response
    q = text(f'''
        SELECT language, numbered_intents
        FROM public.message
        WHERE from_number = '{from_number}'
        ORDER BY id DESC
        LIMIT 1;
        ''')
    
    # Create a database engine and connect to it
    engine = create_engine(postgres_str, echo=False)
    conn = engine.connect()
    
    # Execute the query and fetch the results
    result = conn.execute(q).fetchall()[0]
    
    # Extract language and numbered_intents from the result
    language = result[0]
    options = result[1]
    
    # Close the database connection
    conn.close()
    
    return language, options


def similarity_score(row, target_value):
    """
    Calculate the similarity score between the intent in a row and a target value.

    This function calculates the similarity score between the 'intent' value in a
    given row and a target value using the fuzzy string matching algorithm provided
    by the `fuzz.ratio` function.

    Args:
        row (pandas.Series): A pandas Series representing a row in a DataFrame.
        target_value (str): The target value to compare against.

    Returns:
        int: The similarity score between the row's 'intent' value and the target value.

    Example:
        score = similarity_score(row, 'greeting')
    """
    # Calculate the similarity score using the fuzzy string matching algorithm
    score = fuzz.ratio(row['intent'], target_value)
    return score
