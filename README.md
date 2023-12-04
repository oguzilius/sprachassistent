# Anleitung zur Verwendung dieses Projekts

Dieses Projekt verwendet `Python 3.11.5` und verschiedene Bibliotheken, um einen Sprachassistenten zu erstellen. Bevor Sie das Projekt ausführen können, müssen Sie einige Schritte ausführen.

## Schritt 1: Installieren Sie die erforderlichen Bibliotheken

Verwenden Sie die Datei `requirements.txt`, um die erforderlichen Python-Bibliotheken zu installieren. Öffnen Sie die Befehlszeile oder das Terminal und navigieren Sie zum Hauptverzeichnis des Projekts. Führen Sie dann den folgenden Befehl aus:

```bash
pip install -r requirements.txt
```
Dadurch werden alle in der requirements.txt-Datei aufgeführten Bibliotheken installiert.

## Schritt 2: Erstellen Sie die .env-Datei
Im Verzeichnis `server` dieses Projekts müssen Sie eine .env-Datei erstellen, die wichtige API-Schlüssel und Konfigurationseinstellungen enthält. Öffnen Sie die .env-Datei mit einem Texteditor und fügen Sie die folgenden Informationen ein:

```bash
OPENAI_API_KEY = [Ihr OpenAI API-Schlüssel]

SPEECH_SERVICES_API_KEY = [Ihr Speech Services API-Schlüssel]

REGION = [Die Region auf der die OpenAI und Azure Cognitive Speech services bereitgestellt wurden. z.B. "uksouth"]
```

## Schritt 3: Starten Sie das Projekt
Um das Projekt auszuführen und den Sprachassistenten zu verwenden, führen Sie die `app.py`-Datei im Hauptverzeichnis aus. Verwenden Sie die Befehlszeile oder das Terminal und navigieren Sie zum Hauptverzeichnis, und führen Sie dann den folgenden Befehl aus:

```bash
python server/app.py
```

Der Sprachassistent wird gestartet und kann über `localhost:5001` in Ihrem Webbrowser verwendet werden.

## Weitere Informationen:
Um die Instandhaltungsfunktionen des Sprachssistenten zu benutzen müssen in der `gpt_app.py`-Datei die entsprechenden Adressen und Netzlaufwerkpfade der entsprechenden Maschinen eingesetzt werden.
