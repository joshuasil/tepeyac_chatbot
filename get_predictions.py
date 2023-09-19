import boto3
import pickle
import os
from flask import current_app

AWS_ACCESS_KEY_ID=os.environ.get('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY=os.environ.get('AWS_SECRET_ACCESS_KEY', None)
AWS_COMPREHEND_ENDPOINT=os.environ.get('AWS_COMPREHEND_ENDPOINT', None)

# Create a Comprehend client
client = boto3.client('comprehend', region_name='us-east-1')

# Specify the correct endpoint ARN
endpoint_arn = AWS_COMPREHEND_ENDPOINT


# Call the API and store the response

# Load the dictionary from the pickle file
with open('intent_dict.pkl', 'rb') as file:
    intent_dict = pickle.load(file)

with open('intent_dict_es.pkl', 'rb') as file:
    intent_dict_es = pickle.load(file)

def get_prediction(text,language):
    current_app.logger.info(f"get_prediction called for {text}")
    response = client.classify_document(Text=text, EndpointArn=endpoint_arn)

    # Get the top 5 predicted class labels
    top_intents = [i['Name'] for i in response['Classes']]

    # Get the corresponding probabilities
    if language == 'en':
        top_dialogs = [intent_dict[intent] for intent in top_intents]
        numbered_intents_dict = {i+1:intent for i, intent in enumerate(top_intents)}
        response = 'Are you asking about: \n' + ('\n'.join([f'{i+1}. {intent}' for i, intent in enumerate(top_dialogs)]))
    else:
        top_dialogs = [intent_dict_es[intent] for intent in top_intents]
        numbered_intents_dict = {i+1:intent for i, intent in enumerate(top_intents)}
        response = '¿Estás preguntando sobre: \n' + ('\n'.join([f'{i+1}. {intent}' for i, intent in enumerate(top_dialogs)]))
    current_app.logger.info(f"model prediction used for {text}")
    return response, numbered_intents_dict

