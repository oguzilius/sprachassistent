from flask import Flask, request, render_template, jsonify
from markupsafe import escape
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS
from gpt_app import gptManager
from db_manager import dbManager
load_dotenv()

API_TOKEN = os.getenv('SPEECH_SERVICES_API_KEY')
REGION = os.getenv('REGION')
OPEN_API_KEY = os.getenv('OPENAI_API_KEY')

base_system_message = """
Du unterstützt Fachkräfte auf der Arbeit. Du kannst Fragen bezüglich Fertigungs- und Produktionsumgebungen beantworten und dienst als allgemeine Informationsquelle.
Du schreibst in einem freundlichen professionellen Ton und kannst deine Nachrichten an den Nutzer anpassen.
Zusätzliche Anweisungen:
-Verstehe den Nutzer und frage gegebenenfalls nach, um ihn besser zu verstehen.
-Schreib keinen schädlichen, beleidigenden oder schlecht über ein Produkt oder Unternehmen sprechenden Inhalt.
-Stell dich immer als M-Bot vor. M-Bot ist der Mercedes Benz Bot.
-wenn du undefined als anfrage kriegst sagst du dem nutzer dass die Sprachfunktion eventuell nicht richtig funktioniert und das er versuchen soll die anfrage als text abzutippen
"""

#Erstellen des gptManagers der Datenbank und des Webservers
gpt = gptManager(base_system_message)
db = dbManager()
app = Flask(__name__)
CORS(app)

#Homepage der Webanwendung
@app.route('/')
@app.route('/index')
@app.route('/chat')
def index():
    gpt.flush()
    return render_template('index.html')

#Authentifizierungstoken für Azure Cognitive Speech Services generieren
@app.route('/token', methods=["GET"])
def token():
    url = f"https://{REGION}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
    headers = {
        "Ocp-Apim-Subscription-Key": API_TOKEN,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(url, headers=headers)
    return response.text

#Aufrufen des Sprachmodells
@app.route('/gpt', methods=['POST'])
def gpt_reply():
    received_string = request.form["msg"]

    #relevante Textabschnitte aus der Datenbank laden
    context = db.get_document_context(received_string)
    #Antwort mit dem Kontext generieren
    response = gpt.handle_request(message=received_string, context=context)
    return str(response)

#Löschen der gespeicherten Dateien
@app.route('/delete', methods=['POST'])
def delete_file():
    data = request.get_json()
    filename = data.get('filename')

    # Pfad, in dem die Dateien gespeichert sind
    file_directory = 'server/saved/'
    source = os.path.join("uploads\\", filename)
    # Vollständiger Pfad zur Datei
    file_path = os.path.join(file_directory, filename)

    # Überprüfen, ob die Datei existiert, und löschen
    if os.path.exists(file_path):
        try:
            db.del_entries_by_filename(file_name=source)
            os.remove(file_path)
            return jsonify({'message': 'File successfully deleted'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/upload', methods=['POST'])
def upload_file():
    UPLOAD_FOLDER = 'server/uploads'
    if 'fileToUpload' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['fileToUpload']

    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    # Prüfen ob eine PDF-Datei hochgeladen wurde
    allowed_extensions = {'pdf'}
    file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if file_extension not in allowed_extensions:
        return jsonify({'error': 'Invalid file extension'})

    if file:
        filename = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filename)
        db.add_documents()
        return jsonify({'message': 'File uploaded successfully'})

app.run(port=5001)