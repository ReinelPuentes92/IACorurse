import openai
from dotenv import load_dotenv, find_dotenv

from pynput import keyboard
import sounddevice as sd

#Importaciones para la función Guardar_y_Transcribir
import wave
import os

import numpy as np
import whisper
from queue import Queue
import io
import soundfile as sf
import threading

load_dotenv(find_dotenv())
client = openai.Client()


class TalkingLLM():

    def __init__(self, model="gpt-3.5-turbo", whisper_size="small"):
        self.is_recording = False #Para la Grabación de mi voz
        self.audio_data = [] #Para la Grabación de mi voz
        self.samplerate=44100 #Parámetros para la digitalización de mi voz
        self.channels=1 #Parámetros para la digitalización de mi voz
        self.dtype='int16' #Parámetros para la digitalización de mi voz

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
    #====================================  Paso 3  ================================
    #Ese texto transcrito lo enviamos para el Agente
    def create_agent(self):
        pass
    
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

    #=================================  Paso 4  ==============================
    #El agente devuelve una respuesta que es pasada a esta función para que sea reproducida
    def convert_and_play(self):
        pass



    #===================== FUNCION PRINCIPAL (ORQUESTADOR) ======================
    def run(self):
        print("Estoy corriendo")

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
                keyboard.HotKey.parse('<space>'), #EDITADO
                on_activate) #Copiado de la documentación de pynput
            with keyboard.Listener( #Copiado de la documentación de pynput
                    on_press=for_canonical(hotkey.press), #Copiado de la documentación de pynput
                    on_release=for_canonical(hotkey.release)) as l: #Copiado de la documentación de pynput
                l.join() #Copiado de la documentación de pynput


if __name__ == "__main__":
    #Instanciamos nuestra clase con este objeto
    talking_llm = TalkingLLM()
    #El Objeto llama a la función run que heredó
    talking_llm.run()
