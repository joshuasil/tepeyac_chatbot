import pandas as pd
from tensorflow.keras.models import model_from_json
import pickle
from tensorflow.keras.preprocessing.sequence import pad_sequences
import numpy as np
from flask import current_app


df = pd.read_csv('model_training.csv')

# Load the dictionary from the pickle file
with open('intent_dict.pkl', 'rb') as file:
    intent_dict = pickle.load(file)

with open('intent_dict_es.pkl', 'rb') as file:
    intent_dict_es = pickle.load(file)

# load json and create model
json_file = open('model.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
# load weights into new model
loaded_model.load_weights("model.h5")
print("Loaded model from disk")
# Load the tokenizer
with open('tokenizer.pkl', 'rb') as token_file:
    loaded_tokenizer = pickle.load(token_file)
MAX_SEQUENCE_LENGTH = 125
# Load the reverse mapping dictionary from the pickle file
with open('reverse_mapping.pkl', 'rb') as file:
    loaded_reverse_mapping = pickle.load(file)

def get_prediction(text,language):
    new_classification = [text]
    seq = loaded_tokenizer.texts_to_sequences(new_classification)
    padded = pad_sequences(seq, maxlen=MAX_SEQUENCE_LENGTH)
    pred = loaded_model.predict(padded)[0]
    top_topic_indices = np.argsort(pred)[::-1][:4]
    top_intents = [loaded_reverse_mapping[idx] for idx in top_topic_indices]
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

