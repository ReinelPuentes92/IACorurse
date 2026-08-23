import openai
from dotenv import load_dotenv, find_dotenv

from pynput import keyboard
import sounddevice as sd

#Importaciones para la función Guardar_y_Transcribir
import wave
import os
import numpy as np

import whisper

from langchain.messages import AIMessage

from queue import Queue

import io
import soundfile as sf
import threading

#El agente vive en agent.py: este archivo solo se encarga de la VOZ
from agent import DEFAULT_MODEL, build_agent
from conversation_history import (
    cerrar,
    historial_persistente,
    nueva_sesion,
    registrar_turno,
    validar_sesion,
)

load_dotenv(find_dotenv())

#Sin esta comprobación, openai.Client() falla con un "Missing credentials" que no
#dice cuál es el archivo ni la variable que hay que arreglar.
if not os.getenv("OPENAI_API_KEY"):
    raise SystemExit(
        "\n❌ Falta OPENAI_API_KEY.\n"
        f"   Añádela al archivo .env de {os.path.dirname(os.path.abspath(__file__))}\n"
        "   con el formato:  OPENAI_API_KEY=sk-...\n"
    )

client = openai.Client()


class TalkingLLM():

    def __init__(self, model=DEFAULT_MODEL, whisper_size="small", session_id=None):
        self.is_recording = False #Para la Grabación de mi voz
        self.audio_data = [] #Para la Grabación de mi voz
        self.samplerate=44100 #Parámetros para la digitalización de mi voz
        self.channels=1 #Parámetros para la digitalización de mi voz
        self.dtype='int16' #Parámetros para la digitalización de mi voz

        self.whisper = whisper.load_model(whisper_size) #Part2

        self.llm_queue = Queue() #Part2: Para almacenar lo que respondió mi LLM

        self.agent = build_agent(model) #Part3: LLM + prompt + tools (ver agent.py)

        #Part3: el thread_id es lo que le dice a LangGraph qué conversación releer.
        #Sin él el agente no recuerda nada entre turnos.
        self.session_id = validar_sesion(session_id) if session_id else nueva_sesion()
        self.config = {
            "configurable": {"thread_id": self.session_id},
            "recursion_limit": 50,
        }

    #==============================================================================
    #====================================  Paso 1  ================================
    def start_or_stop_recording(self):
        if self.is_recording: #Si estoy grabando
            self.is_recording = False #Quiero parar de grabar
            self.save_and_transcribe() #Vamos a guardar el audio y transcribir
            self.audio_data = [] #Luego elimino lo que grabé, porque quiero comenzar de nuevo a grabar tal vez
        else:
            print("Starting record") #Si no estoy grabando, EMPIEZO
            self.audio_data = [] #Listo para guardar lo que hable
            self.is_recording = True #Comienzo a grabar

    #==============================================================================
    #===================================  Paso 2  =================================
    #Guardamos nuestro audio y transcribimos para texto
    def save_and_transcribe(self):
        print("Saving the recording...")
        if "temp.wav" in os.listdir(): os.remove("temp.wav") #Si tengo un archivo de audio temporal lo elimino
        wav_file = wave.open("test.wav", 'wb') #Ahora creo un archivo de audio
        wav_file.setnchannels(self.channels)
        wav_file.setsampwidth(2)  # Corregido para usar la longitud de muestra para int16 directamente
        wav_file.setframerate(self.samplerate)
        wav_file.writeframes(np.array(self.audio_data, dtype=self.dtype)) #Transfiere mi audio_data a un array
        wav_file.close()

        result = self.whisper.transcribe("test.wav", fp16=False)
        print("Usuario:", result["text"])

        #Paso 3: ese texto transcrito lo enviamos al Agente (definido en agent.py).
        #self.config lleva el thread_id: por eso el agente recuerda los turnos previos.
        response = self.agent.invoke(
            {"messages": [{"role": "user", "content": result["text"]}]},
            self.config,
        )

        ai_message = "Sin respuesta."
        for msg in reversed(response.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content:
                ai_message = msg.content
                break

        print("AI:", ai_message)
        registrar_turno(self.session_id, result["text"], ai_message) #log legible con SQL
        self.llm_queue.put(ai_message)

    #=================================  Paso 4  ==============================
    #El agente devuelve una respuesta que es pasada a esta función para que sea reproducida
    def convert_and_play(self):
        tts_text = ''
        while True:
            tts_text += self.llm_queue.get()

            if '.' in tts_text or '?' in tts_text or '!' in tts_text:
                #El texto ya se imprimió en save_and_transcribe ("AI: ..."); aquí
                #solo indicamos que arranca el audio, para no duplicar la salida.
                print("🔊 Reproduciendo...")

                spoken_response = client.audio.speech.create(model="tts-1",
                voice='alloy', 
                response_format="opus",
                input=tts_text
                )

                buffer = io.BytesIO()
                for chunk in spoken_response.iter_bytes(chunk_size=4096):
                    buffer.write(chunk)
                buffer.seek(0)

                with sf.SoundFile(buffer, 'r') as sound_file:
                    data = sound_file.read(dtype='int16')
                    sd.play(data, sound_file.samplerate)
                    sd.wait()
                tts_text = ''



    #===================== FUNCION PRINCIPAL (ORQUESTADOR) ======================
    def run(self):
        print("=" * 70)
        print("🎙️  Mantén pulsado <cmd> para hablar; suéltalo para enviar")
        print(f"📝 Session ID: {self.session_id}")
        if historial_persistente():
            print("   (guárdalo: con VOICE_SESSION_ID puedes retomar esta conversación)")
        print("=" * 70)

        t1 = threading.Thread(target=self.convert_and_play, daemon=True)
        t1.start()

        #Esta parte de aquí es bien difícil de implementar si no fuera por la documentación que explica bastante.

        def callback(indata, frame_count, time_info, status): #Copiado de la documentación de sounddevice
            if self.is_recording: #Copiado de la documentación de sounddevice
                self.audio_data.extend(indata.copy()) #Copiado de la documentación de sounddevice

        #Abrimos una instancia de Grabación de Audio en formato de Stream
        with sd.InputStream(samplerate=self.samplerate, #Copiado de la documentación de sounddevice
                            channels=self.channels, #Copiado de la documentación de sounddevice
                            dtype=self.dtype , #Copiado de la documentación de sounddevice
                            callback=callback): #Copiado de la documentación de sounddevice
            
            def on_activate(): #Copiado de la documentación de pynput
                self.start_or_stop_recording() #EDITADO

            def for_canonical(f): #Copiado de la documentación de pynput
                return lambda k: f(l.canonical(k)) #Copiado de la documentación de pynput

            hotkey = keyboard.HotKey( #Copiado de la documentación de pynput
                keyboard.HotKey.parse('<cmd>'), #EDITADO
                on_activate) #Copiado de la documentación de pynput
            with keyboard.Listener( #Copiado de la documentación de pynput
                    on_press=for_canonical(hotkey.press), #Copiado de la documentación de pynput
                    on_release=for_canonical(hotkey.release)) as l: #Copiado de la documentación de pynput
                l.join() #Copiado de la documentación de pynput


if __name__ == "__main__":
    #Si exportas VOICE_SESSION_ID=<uuid> retomas una conversación anterior;
    #si no, se crea una sesión nueva.
    talking_llm = TalkingLLM(session_id=os.getenv("VOICE_SESSION_ID"))
    try:
        #El Objeto llama a la función run que heredó
        talking_llm.run()
    except KeyboardInterrupt:
        print(f"\n💾 Sesión guardada: {talking_llm.session_id}")
    finally:
        cerrar() #cierra la conexión del histórico
