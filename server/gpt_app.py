import os
import openai
import json
import tiktoken
from datetime import datetime, timedelta
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
import time
load_dotenv()

energie_antwort = None

#rechnet aus wie viele Teile in den letzten n Tagen fehlerhaft waren indem
#im Qualitätsdatenordner nachgesehen wird
def files_of_last_few_days(days=3):
    base_path = "" #Netzwerkpfad wo die Qualitätsdaten hochgeladen werden (Darf nicht mit hochgeladen werden)
    today = datetime.today()
    files = []

    for i in range(days):
        target_date = today - timedelta(days=i)
        target_date_str = target_date.strftime("%Y/%m/%d")
        target_file_path = os.path.join(base_path, target_date_str)
        if os.path.exists(target_file_path):
            for file in os.listdir(target_file_path):
                files.append(os.path.join(target_file_path, file))

    return files

def energy_data():
    # MQTT-Broker-Konfiguration
    broker_address = "" #Adresse der Schleifmaschine (Darf nicht mit hochgeladen werden)
    broker_port = 1883
    topic = "" #Topic der Energiedaten wählen
    global energie_antwort

    # Callback-Funktion, die aufgerufen wird, wenn eine Nachricht empfangen wird
    def on_message(client, userdata, message):
        # Energiedaten verarbeiten
        energiedaten = message.payload.decode("utf-8")
        
        # Antwort formulieren
        global energie_antwort
        energie_antwort = f"Der aktuelle Energieverbrauch beträgt {energiedaten} Watt."
        
        # Verbindung beenden
        client.disconnect()

    # MQTT-Client initialisieren
    client = mqtt.Client()
    client.on_message = on_message

    # Mit dem Broker verbinden
    client.connect(broker_address, broker_port)
    client.subscribe(topic)

    # Auf Nachrichten warten für maximal 5 Sekunden
    client.loop_start()
    timeout = time.time() + 5
    while time.time() < timeout and energie_antwort is None:
        pass
    client.loop_stop()
    # Die empfangene Nachricht kann nun außerhalb der Schleife verwendet werden
    if energie_antwort is not None:
        #reset ermittelten Energiewert da er nicht mehr aktuell ist
        antwort = energie_antwort
        energie_antwort = None
        return antwort
    else:
        return "Die Maschine Antwortet derzeit nicht."

#lädt aus text-dateien aus prompt_templates, in denen beispielanfragen definiert sind für die few-shot prompts 
def get_template_from_file(file_name):
    try:
        folder = "server/prompt_templates"
        file_name = file_name + ".txt"
        file_path = os.path.join(folder, file_name)

        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
            file.close()
        return file_content
    except FileNotFoundError:
        return "Datei nicht gefunden."
    except Exception as e:
        return f"Fehler beim Lesen der Datei: {str(e)}"
    
class gptManager:
    def __init__(self, system_message, prompt_max_tokens = 4000) -> None:
        self.system_message = f"<|im_start|>System: {system_message.strip()}\n<|im_end|>"
        self.context = ""
        self.messages = []     
        self.prompt_max_tokens = prompt_max_tokens   
        # Konfiguration
        with open(r'server/config.json') as config_file:
            config_details = json.load(config_file)
        
        self.chatgpt_model_name = config_details['CHATGPT_MODEL']
        openai.api_type = "azure"
        openai.api_key = os.getenv("OPENAI_API_KEY")
        openai.api_base = config_details['OPENAI_API_BASE']
        openai.api_version = config_details['OPENAI_API_VERSION']

    
    # Funktion zum Erstellen des Prompts aus Systemnachricht und Nachrichten
    # Die Funktion nimmt an, dass `messages` eine Liste von Dictionaries mit `sender` und `text` ist
    def create_prompt(self):
        prompt = ""
        prompt += self.system_message
        prompt += self.context
        for message in self.messages:
            prompt += f"\n<|im_start|>{message['sender']}: { message['text']}\n<|im_end|>"
        prompt += "\n<|im_start|>assistant\n"
        return prompt
    
    # Funktion zum Erstellen einer Anweisung
    @staticmethod
    def create_instruction(instruction):
        instruction = f"\n{instruction}"
        return instruction
    
    # Funktion zur Formatierung einer Programmfrage und des Kontexts
    @staticmethod
    def format_program_query(user_query, program_query, context):
        response = f"Benutzeranfrage: {user_query}\n"
        response += f"Programmfrage: {program_query}\n"
        response += f"Kontext: {context}\n"
        response += f"Antwort:"
        return response

    # Funktion zur Schätzung der Anzahl der Tokens in einem Prompt
    @staticmethod
    def estimate_tokens(prompt):
        cl100k_base = tiktoken.get_encoding("cl100k_base") 

        enc = tiktoken.Encoding( 
            name="chatgpt",  
            pat_str=cl100k_base._pat_str, 
            mergeable_ranks=cl100k_base._mergeable_ranks, 
            special_tokens={ 
                **cl100k_base._special_tokens, 
                "<|im_start|>": 100264, 
                "<|im_end|>": 100265
            } 
        ) 

        tokens = enc.encode(prompt,  allowed_special={"<|im_start|>", "<|im_end|>"})
        return len(tokens)


    # Funktion zum Senden einer Nachricht an das GPT-Modell
    def send_message(self, message, model_name = None, max_response_tokens=500):
        
        if model_name is None:
            model_name = self.chatgpt_model_name

        self.messages.append({"sender": "user", "text": message})
        prompt = self.create_prompt()
        token_count = self.estimate_tokens(prompt)

        # remove first message while over the token limit
        while token_count > self.prompt_max_tokens:
            self.messages.pop(0)
            prompt = self.create_prompt()
            token_count = self.estimate_tokens(prompt)

        response = openai.Completion.create(
            engine=model_name,
            prompt=prompt,
            temperature=0.9,
            max_tokens=max_response_tokens,
            top_p=0.9,
            frequency_penalty=0,
            presence_penalty=0,
            stop=['<|im_end|>']
        )
        response_text = response['choices'][0]['text'].strip()
        self.messages.append({"sender": "assistant", "text": response_text})
        return response_text
    
    # Funktion zum Senden einer Anweisung an das GPT-Modell
    def send_instruction(self, instruction, model_name = None, max_response_tokens=50):
        
        if model_name is None:
            model_name = self.chatgpt_model_name

        instruction_prompt = self.create_instruction(instruction)
        token_count = self.estimate_tokens(instruction_prompt)

        # remove first message while over the token limit
        if token_count > self.prompt_max_tokens:
            return 3

        response = openai.Completion.create(
            engine=model_name,
            prompt=instruction_prompt,
            temperature=0.9,
            max_tokens=max_response_tokens,
            top_p=0.9,
            frequency_penalty=0,
            presence_penalty=0,
            stop=['<|im_end|>']
        )
        response_text = response['choices'][0]['text'].strip()
        return response_text
    
    # Zurücksetzen der Nachrichtenliste
    def flush(self):
        self.messages = []
            
    def machine_chain(self, message, model_name = None, max_response_tokens=500):
        # Die Benutzeranfrage wird formatiert und an das Modell gesendet, um festzustellen,
        # ob sie sich auf eine Schleifmaschine bezieht
        context_template = get_template_from_file("is_schleifmaschine")
        formatted_message = self.format_program_query(user_query = message, program_query = "Bezieht sich die Benutzeranfrage auf eine Schleifmaschine?", context="Wenn die Programmfrage zutrifft ist die Antwort 1, andernfalls 0 und wenn nicht genau gesagt werden kann ob es stimmt oder nicht ist die Antwort 2. Die Antwort darf nur eine Zahl beinhalten.")
        request_message = context_template + formatted_message
        is_schleifmaschine_request = int(self.send_instruction(request_message))

        if is_schleifmaschine_request == 1:
            # Die Benutzeranfrage wird erneut formatiert und an das Modell gesendet, um festzustellen,
            # ob sie sich auf den Verlauf der Qualitätsdaten bezieht
            context_template = get_template_from_file("is_qualdata")
            formatted_message = self.format_program_query(user_query = message, program_query = "Bezieht sich die Benutzeranfrage auf den Verlauf der Qualitätsdaten?", context="Wenn die Programmfrage zutrifft ist die Antwort 1, andernfalls 0 und wenn nicht genau gesagt werden kann ob es stimmt oder nicht ist die Antwort 2. Die Antwort darf nur eine Zahl beinhalten.")
            request_message = context_template + formatted_message
            is_qual_request = int(self.send_instruction(request_message))

            if is_qual_request == 1:
                # Wenn die Anfrage auf Qualitätsdaten bezogen ist, werden die Daten der letzten 7 Tage abgerufen
                days = 7
                files = files_of_last_few_days(days)
                response = f"In den letzten {days} Tagen wurden {len(files)} fehlerhafte Teil(e) produziert."
                return response
            
            # Die Benutzeranfrage wird erneut formatiert und an das Modell gesendet, um festzustellen,
            # ob sie sich auf die Energiedaten bezieht
            context_template = get_template_from_file("is_energydata")
            formatted_message = self.format_program_query(user_query = message, program_query = "Bezieht sich die Benutzeranfrage auf die Energiedaten?", context="Wenn die Programmfrage zutrifft ist die Antwort 1, andernfalls 0 und wenn nicht genau gesagt werden kann ob es stimmt oder nicht ist die Antwort 2. Die Antwort darf nur eine Zahl beinhalten.")
            request_message = context_template + formatted_message
            is_energy_request = int(self.send_instruction(request_message))
            
            if is_energy_request:
                # Wenn die Anfrage auf Energiedaten bezogen ist, werden die entsprechenden Daten abgerufen
                return energy_data()
        #Fallback               
        return self.send_message(message=message)


    def handle_request(self, message, context, model_name = None, max_response_tokens=500):
        self.context = context
        context_template = get_template_from_file("is_machine")
        formatted_message = self.format_program_query(user_query = message, 
                                                      program_query = "Bezieht sich die Benutzeranfrage auf eine Maschine?", 
                                                      context =  "Wenn die Programmfrage zutrifft ist die Antwort 1, andernfalls 0 und wenn nicht genau gesagt werden kann ob es stimmt oder nicht ist die Antwort 2. Die Antwort darf nur eine Zahl beinhalten.")
        request_message = context_template + formatted_message

        is_machine_request = int(self.send_instruction(request_message))

        #Falls die Anfrage auf eine Machine bezogen ist wird die machine_chain aufgerufen um Maschinendaten zu laden
        if is_machine_request == 1:           
            return self.machine_chain(message, model_name = None, max_response_tokens=max_response_tokens)
        #Fallback
        return self.send_message(message=message)

