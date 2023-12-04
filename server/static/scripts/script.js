var access_token;
var voice_data;
var voice_actor;
var audio_response;
var dropped_file;
var recorder;
var audio_duration;
var audio_elem;
let API_ENDPOINT = 'http://localhost:5001';
let websocket;
var recording = false;

function sendMessage(input) {
    //nachsehen ob der parameter input manuell gesetzt wurde, ansonsten aus dem textfeld die eingabe auslesen
    if (input === undefined) {
        message = document.getElementById("messageInput").value;
    } else {
        message = input
    }

    // aktualisiere das chatfenster mit der nutzereingabe
    if (message.trim() !== '') {
        document.getElementById("chatBox").innerHTML += "<div class='message userMessage'><div class='profileImage'><img src=\"https://i.ibb.co/d5b84Xw/Untitled-design.png\"></div>" + message + "</div>";
        document.getElementById("chatBox").scrollTop = document.getElementById("chatBox").scrollHeight;
    } else {
        return;
    }
    const formData = new FormData();

    formData.append('msg', message);

    // fetch Anfrage mit der Nachricht des Nutzers erstellen und an den Webserver schicken
    fetch(API_ENDPOINT + "/gpt", {
            method: 'POST',
            body: formData
        })
        .then(response => response.text())
        .then(data => {
            //antwort vom Webserver in audio konvertieren und den text ins chatfenster einfügen
            getMp3(data); 
            document.getElementById("chatBox").innerHTML += "<div class='message assistantMessage'><div class='profileImage'><img src=\"https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Mercedes-Benz_free_logo.svg/2046px-Mercedes-Benz_free_logo.svg.png\"></div>" + data + "</div>";
            document.getElementById("messageInput").value = "";
            document.getElementById("chatBox").scrollTop = document.getElementById("chatBox").scrollHeight;
        });
}

// wenn die Enter Taste gedrückt wird soll die Nachricht geschickt werden
function handleKeyPress(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
}

//verstecke das Lösch-Fenster
function hide_delete_window() {
    document.getElementById("deleteFilePopup").style.display = "none";
    document.getElementById("deleteFileName").value = '';
}

//schicken neuer PDF-Dateien an den Webserver
function uploadFile() {
    var fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.pdf'; // akzeptierte Dateitypen
    
    // sobald eine datei ausgewählt wurde:
    fileInput.onchange = function(event) {
        var selectedFile = event.target.files[0];
        if (selectedFile) {
            var formData = new FormData();
            formData.append('fileToUpload', selectedFile);

            // Datei mit der Fetch API an den Webserver schicken
            fetch(`${API_ENDPOINT}/upload`, {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.text())
                .then(data => {
                    alert('File uploaded successfully');
                })
                .catch(error => {
                    alert('Error uploading file');
                });
        }
    };
    fileInput.click();
}

//text in audio convertieren mit den cognitive speach services von azure
function getMp3(text) {
    fetch("https://uksouth.tts.speech.microsoft.com/cognitiveservices/v1", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/ssml+xml',
                'Authorization': 'Bearer ' + access_token,
                'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3'
            },
            body: get_ssml(text)
        })
        .then(response => response.blob())
        .then(blob => {
            const audio = new Audio(URL.createObjectURL(blob));
            audio.play();
        });
}


//ssml generieren, welche die eigenschaften der stimme beschreibt die den text sprechen soll
function get_ssml(text) {
    let voice_actor_name = "de-DE-KatjaNeural";
    let lang = "de-DE";
    let gender = "Female";
    rate = 30;
    pitch = 0;

    //no speaking style selected
    let ssml = `<speak version="1.0" xml:lang="${lang}"><voice xml:lang="${lang}" xml:gender="${gender}" name="${voice_actor_name}"><prosody rate="${rate}%" pitch="${pitch}%">${text}</prosody></voice></speak>`;

    return ssml;
}

//webserver nach einem authentifizierungstoken für die cognitive speech services von azure fragen
function setup() {
    fetch(`${API_ENDPOINT}/token`)
        .then(response => response.text())
        .then(data => {
            access_token = data;
        })
        .catch(error => {
            console.error('Error:', error);
        });
}
setup();

$(document).ready(function() {

    //gesprochenes in text umwandeln
    function recognize_speech() {
        const str_time = new Date().toLocaleTimeString('de-DE', {
            hour: '2-digit',
            minute: '2-digit'
        });

        //Anfrage an azure cognitive services mit der aufgenommenen audiodatei die in text umgewandelt werden soll
        fetch("https://uksouth.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=de-DE&format=detailed", {
                method: 'POST',
                headers: {
                    "Authorization": "Bearer " + access_token,
                    "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                    "Accept": "application/json;text/xml"
                },
                body: dropped_file
            })
            .then(response => response.json())
            .then(recognition => {
                const rawText = recognition.DisplayText;

                sendMessage(rawText);
            });
    }

    const recordAudio = () =>
        new Promise(async (resolve) => {
            // Setzen des MediaRecorders auf OpusMediaRecorder
            window.MediaRecorder = OpusMediaRecorder;
            OpusMediaRecorder;
            const workerOptions = {
                OggOpusEncoderWasmPath: "https://cdn.jsdelivr.net/npm/opus-media-recorder@latest/OggOpusEncoder.wasm",
                WebMOpusEncoderWasmPath: "https://cdn.jsdelivr.net/npm/opus-media-recorder@latest/WebMOpusEncoder.wasm",
            };
            // Optionsobjekt für die Aufnahme
            const options = {
                mimeType: "audio/wav"
            };
            
            // Zugriff auf das Mikrofon des Benutzers anfordern
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: true
            });
            // Einrichten des MediaRecorders
            let recorder = new OpusMediaRecorder(stream, options, workerOptions);
            // Array zum Speichern der Audio-Datenchunks
            const audioChunks = [];

            // Eventlistener für das Empfangen von Datenchunks
            recorder.addEventListener("dataavailable", (event) => {
                audioChunks.push(event.data);
            });

            // Funktion zum Starten der Aufnahme
            const start = () => recorder.start();
            
            // Funktion zum Stoppen der Aufnahme
            const stop = () =>
                new Promise((resolve) => {
                    recorder.addEventListener("stop", () => {
                        // Erstellen eines Blob-Objekts aus den Audio-Datenchunks
                        const audioBlob = new Blob(audioChunks, {
                            type: "audio/wav"
                        });
                        // Erzeugen einer URL für das Blob-Objekt
                        const audioUrl = URL.createObjectURL(audioBlob);
                        // Erzeugen eines Audio-Elements aus der URL
                        const audio = new Audio(audioUrl);
                        // Funktion zum Abspielen der Audiodatei
                        const play = () => audio.play();
                        resolve({
                            audioBlob,
                            audioUrl,
                            play
                        });
                    });

                    recorder.stop();
                });

            resolve({
                start,
                stop
            });
        });



    (async () => {
        // Abrufen des Mikrofon-Buttons
        mic_btn = document.getElementById("mic");
        mic_btn.addEventListener(
            "click",
            async () => {
                    event.preventDefault(); // verhindern des submits
                    const iconElement = document.querySelector("#mic i");

                    if (!recording) {
                        mic_btn.disabled = true;
                        iconElement.classList.remove("fa-microphone");

                        iconElement.classList.add("fa-square");
                        
                        // Aufnahme starten
                        recorder = await recordAudio();
                        recorder.start();
                        mic_btn.disabled = false;
                        recording = true;

                    } else {
                        iconElement.classList.remove("fa-square");

                        iconElement.classList.add("fa-microphone");

                        // Aufnahme stoppen
                        const audio = await recorder.stop();
                        recording = false;
                        //audio.play();

                        // Neue Audiodatei aus den Aufnahmen erstellen
                        dropped_file = new File([audio.audioBlob], "test.wav", {
                            type: "audio/wav",
                            lastModified: new Date().getTime(),
                        });
                        // Spracherkennung durchführen
                        recognize_speech();
                    }
                },
                false
        );
    })();
});

// Funktion zum Anzeigen des Lösch-Popups für Dateien
function showDeleteFilePopup() {
    document.getElementById("deleteFilePopup").style.display = "block";
}

// Funktion zum Löschen einer Datei
function deleteFile() {
    var fileName = document.getElementById("deleteFileName").value;
    if (fileName.trim() === '') {
        alert("Bitte geben Sie einen Dateinamen ein.");
        return;
    }

    // Anfrage zum Löschen der Datei an den Server senden
    fetch(`${API_ENDPOINT}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: fileName
            })
        })
        .then(response => {
            if (!response.ok) {
                throw response;
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                alert('Fehler beim Löschen der Datei: ' + data.error);
            } else {
                alert('Datei erfolgreich gelöscht');
            }
            hide_delete_window()
        })
        .catch(errorResponse => {
            errorResponse.json().then(errorData => {
                alert('Fehler beim Löschen der Datei: ' + (errorData.error || 'Unbekannter Fehler'));
            }).catch(() => {
                alert('Fehler beim Löschen der Datei');
            });
        });
}