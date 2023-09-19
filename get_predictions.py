import joblib
from flask import current_app
import pickle

# Load the trained model when the app starts
sk_model = joblib.load('text_classifier_model.pkl')

# Load the TF-IDF vectorizer
vectorizer = joblib.load('tfidf_vectorizer.pkl')

# Load the dictionary from the pickle file
with open('intent_dict.pkl', 'rb') as file:
    intent_dict = pickle.load(file)

with open('intent_dict_es.pkl', 'rb') as file:
    intent_dict_es = pickle.load(file)

def get_prediction(text,language):
    current_app.logger.info(f"get_prediction called for {text}")
    input_text_vec = vectorizer.transform([text])
    # Get class probabilities for the input text
    current_app.logger.info(f"step before prediction")
    class_probabilities = sk_model.predict_proba(input_text_vec)
    current_app.logger.info(f"step after prediction")
    # Get the top 5 predicted class indices
    top_4_indices = class_probabilities.argsort()[0][-4:][::-1]

    # Assuming you have a list of class labels (e.g., unique topics)
    class_labels = sk_model.classes_

    # Get the top 5 predicted class labels
    top_intents = [class_labels[i] for i in top_4_indices]

    # Get the corresponding probabilities
    top_4_probabilities = class_probabilities[0, top_4_indices]
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

