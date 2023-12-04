import openai
from langchain.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
import json
import os, shutil

from langchain.document_loaders import TextLoader, PyPDFDirectoryLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma

#Konfiguration
load_dotenv()
with open(r'server/config.json') as config_file:
    config_details = json.load(config_file)

chatgpt_model_name = config_details['CHATGPT_MODEL']
openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = config_details['OPENAI_API_BASE']
openai.api_version = config_details['OPENAI_API_VERSION']




class dbManager:
    def __init__(self):
        # Festlegen des Bereitstellungsnamens für das ChatGPT-Modell aus den Konfigurationsdetails
        self.chatgpt_model_name = config_details['CHATGPT_MODEL']

        # Setzen der Umgebungsvariablen
        openai.api_type = "azure"
        openai.api_key = os.getenv("OPENAI_API_KEY")
        openai.api_base = config_details['OPENAI_API_BASE']
        openai.api_version = config_details['OPENAI_API_VERSION']

        # Definieren des Verzeichnisses zur Speicherung der Chroma-Datenbank
        chroma_directory = 'db/'

        # Initialisieren von Chroma mit den angegebenen Einstellungen, einschließlich einer Einbettungsfunktion von OpenAI
        self.db = Chroma(
            persist_directory=chroma_directory,
            embedding_function=OpenAIEmbeddings(deployment_id="embed-ada", chunk_size=4)
    )

    def add_documents(self, directory="server\\uploads"):
        #PDF-Dokumente aus dem angegebenen Verzeichnis laden und deren Inhalt in Abschnitte aufteilen
        raw_documents = PyPDFDirectoryLoader(directory).load()
        #Durchschnittlich 322 Zeichen pro Absatz
        text_splitter = CharacterTextSplitter(separator="\n", chunk_size=644)
        documents = text_splitter.split_documents(raw_documents)

        # Einträge, die aus diesen Dokumenten stammen, löschen, falls bereits vorhanden
        for doc in raw_documents:
            source = doc.metadata['source']
            self.del_entries_by_filename(file_name=source)
            
            #Dateien aus server/saved löschen, wenn sie erneut hochgeladen werden
            source = doc.metadata['source']
            dest = source.split("\\")[-1]
            dest_path = os.path.join("server\saved", dest)
            if os.path.exists(dest_path):
                print("Zieldatei existiert bereits. Sie wird ersetzt.")
                os.remove(dest_path)

        # Dokumente zur Datenbank hinzufügen
        if len(documents) > 0:
            self.db.add_documents(documents=documents)

        for doc in raw_documents:
            source = doc.metadata['source']
            # Dateipfad aufteilen und nur den Dateinamen nehmen
            dest = source.split("\\")[-1]
            dest_path = os.path.join("server\saved", dest)
            try:
                # Dateien, die bereits zur Datenbank hinzugefügt wurden, in das saved-Verzeichnis verschieben
                os.rename(source, dest_path)
                print("File has been successfully moved.")
            except OSError as e:
                print(f"File move operation failed: {e}")
        


    def del_entries_by_filename(self, file_name):
        # Die aktuelle Sammlung von Einträgen aus der Datenbank abrufen
        coll = self.db.get()
        # Eine Liste für die zu löschenden IDs erstellen
        del_ids = []

        # Durch die vorhandenen Einträge in der Sammlung iterieren
        for i in range(len(coll['ids'])):

            id = coll['ids'][i]
            metadata = coll['metadatas'][i]
            source_file = metadata['source']
            # Überprüfen, ob die Quelldatei dem angegebenen Dateinamen entspricht
            # Wenn ja, die ID zur Liste der zu löschenden IDs hinzufügen
            if f"{source_file}" == file_name:
                del_ids.append(id)

        # Wenn es IDs zum Löschen gibt, diese aus der Datenbank entfernen
        if len(del_ids) > 0:
            self.db._collection.delete(del_ids)
    
    def del_all(self):
        # Die aktuelle Sammlung von Einträgen aus der Datenbank abrufen
        coll = self.db.get()
        # Eine Liste für die zu löschenden IDs erstellen
        del_ids = []

        #Alle vorhandenen Dateien löschen
        for i in range(len(coll['ids'])):
            id = coll['ids'][i]
            del_ids.append(id)

        if len(del_ids) > 0:
            self.db._collection.delete(del_ids)
    
    def get_document_context(self, query):
        try:
            # Ähnliche Dokumente basierend auf der Abfrage in der Datenbank suchen (k=12 für 12 Ergebnisse)
            docs = self.db.similarity_search(query, k=12)
            # Eine Liste zur Speicherung einzelner Seiteninhalte verwenden
            content_list = []

            # Durch die gefundenen Dokumente iterieren
            for doc in docs:
                # Den Seiteninhalt des Dokuments zur Liste hinzufügen
                content_list.append(doc.page_content)

            # Seiteninhalte durch Zeilenumbrüche trennen und zusammenführen
            content = "\n\n".join(content_list)
            return content

        except Exception as e:
            return f"An error occurred: {e}"