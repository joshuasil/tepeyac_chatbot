import pandas as pd
from get_predictions import *
import json
from handlers import *
from flask import current_app

df = pd.read_excel('responses.xlsx',engine='openpyxl')




def get_response(text, intent, confidence, language):
    """
    Get a response and related intents based on input intent and confidence.

    This function determines the response and related intents to provide based on the
    input intent and confidence score. If the confidence score is high (greater than 0.85),
    it retrieves the appropriate response and related intents from the DataFrame based on
    the input intent. If the confidence score is lower, it falls back to a prediction-based
    response using the `get_prediction` function.

    Args:
        text (str): The input text.
        intent (str): The detected intent of the input text.
        confidence (float): The confidence score of the detected intent.
        language (str): The language of the input text ('en' or other).

    Returns:
        tuple: A tuple containing the response text (str), a formatted list of numbered
        related intents (str), and a dictionary of numbered intents and their related
        intent names (dict).

    Example:
        response, numbered_intents, numbered_intents_dict = get_response('Tell me about dogs', 'animal_info', 0.92, 'en')
    """
    current_app.logger.info(f"get_response called for {text} with confidence {confidence}")
    if confidence > 0.85:
        try:
            # Filter the DataFrame to get the row with the specified intent
            filtered_row = df[df['intent'] == intent].iloc[0]
        except IndexError as e:
            temp_df = df.copy()
            # Apply similarity_score function to each row and create a new column
            temp_df['Similarity'] = temp_df.apply(similarity_score, axis=1)
            # Find the row with the highest similarity score
            filtered_row = temp_df[temp_df['Similarity'] == temp_df['Similarity'].max()].iloc[0]
            current_app.logger.error(f"IndexError encountered: {e}")
            current_app.logger.error(f"No intent found for {intent} in {language}! Using {filtered_row['intent']} instead.")
            current_app.logger.info(f"text similarity used to get intent")
        
        # Extract related intents from the filtered row
        related_intents = [value for value in filtered_row[['related_intent_1', 'related_intent_2', 'related_intent_3', 'related_intent_4']] if pd.notnull(value)]
        related_intents = [df[df['dialog'] == value]['intent'].values[0] for value in related_intents]
        
        # Create a dictionary of numbered intents and their related intent names
        numbered_intents_dict = {i + 1: intent for i, intent in enumerate(related_intents)}
        
        if language == 'en':
            # Set the response and related intents for English language
            response = filtered_row['response']
            response_1 = filtered_row['response_1']
            related_intents = [value for value in filtered_row[['related_intent_1', 'related_intent_2', 'related_intent_3', 'related_intent_4']] if pd.notnull(value)]
            numbered_intents = '\n'.join([f'{i + 1}. {intent}' for i, intent in enumerate(related_intents)])
            numbered_intents = response_1 + '\n\n' + 'Ask me about something else:\n' + numbered_intents
        else:
            # Set the response and related intents for non-English languages
            response = filtered_row['response_es']
            response_1 = filtered_row['response_1_es']
            related_intents = [value for value in filtered_row[['related_intent_1_es', 'related_intent_2_es', 'related_intent_3_es', 'related_intent_4_es']] if pd.notnull(value)]
            numbered_intents = '\n'.join([f'{i + 1}. {intent}' for i, intent in enumerate(related_intents)])
            numbered_intents = response_1 + '\n\n' + 'Pregúntame sobre otra cosa:\n' + numbered_intents
    else:
        # If confidence is lower, get prediction-based response and empty numbered intents
        current_app.logger.info(f"confidence too low, using model prediction")
        response, numbered_intents_dict = get_prediction(text, language)
        numbered_intents = ''
        
    return response, numbered_intents, numbered_intents_dict


    
def get_response_picklist(num, from_number):
    """
    Get a response and related intents based on the selected picklist option.

    This function retrieves the language and picklist options for the user from the
    database, then uses the selected picklist option number to determine the associated
    intent. It then gets the response and related intents based on the selected intent.

    Args:
        num (int): The selected picklist option number.
        from_number (str): Sender's phone number.

    Returns:
        tuple: A tuple containing the response text (str), a formatted list of numbered
        related intents (str), a dictionary of numbered intents and their related intent
        names (dict), and the language (str).

    Example:
        response, numbered_intents, numbered_intents_dict, language = get_response_picklist(2, '+1234567890')
    """
    try:
        # Retrieve language and options from the last response for the user
        language, options = get_last_response(from_number)
        options = json.loads(options)
        
        # Get the intent associated with the selected picklist option
        intent = options[str(num)]
        
        # Get response and related intents based on the selected intent
        response, numbered_intents, numbered_intents_dict = get_response('', intent, 1, language)
        
        # Log successful picklist response retrieval
        current_app.logger.info(f"picklist response found for user {from_number}")
        
        return response, numbered_intents, numbered_intents_dict, language
    except KeyError as e:
        # If KeyError occurs, log the error and return an error response
        language, options = get_last_response(from_number)
        options = json.loads(options)
        current_app.logger.error(f"KeyError encountered: {e}")
        
        # Return appropriate error response (modify based on your use case)
        return "Error: Invalid option selected", [], options, language


