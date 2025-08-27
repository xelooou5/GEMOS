#!/usr/bin/env python3
"""
💎 GEM OS - Real-Time Voice Interface
Handles wake-word detection, listening, transcription, and speaking.
English first, Portuguese (pt-BR) second.
"""
import asyncio
import sounddevice as sd
import numpy as np
import boto3
from botocore.exceptions import NoCredentialsError
from google.cloud import speech
import os
import wave
import pvporcupine
import struct
import webrtcvad
from collections import deque

class VoiceInterface:
    def __init__(self, language_code: str, polly_voice: str, wake_word: str):
        # --- General Config ---
        self.language_code = language_code
        self.polly_voice = polly_voice
        self.accessibility_mode = False
        self.is_speaking = False

        # --- Audio Config ---
        self.samplerate = 16000  # 16kHz is standard for voice
        self.channels = 1
        self.dtype = 'int16'
        self.frame_duration_ms = 30  # VAD requires 10, 20, or 30 ms frames
        self.frame_size = int(self.samplerate * self.frame_duration_ms / 1000)

        # --- AWS Polly (TTS) ---
        try:
            self.polly = boto3.client('polly')
            print("✅ AWS Polly client for speech initialized.")
        except NoCredentialsError:
            print("⚠️ AWS credentials not found. Text-to-speech will be simulated.")
            self.polly = None

        # --- Google Speech-to-Text (Transcription) ---
        try:
            self.speech_client = speech.SpeechClient()
            print("✅ Google Speech-to-Text client initialized.")
        except Exception as e:
            print(f"⚠️ Google Speech-to-Text client failed to initialize: {e}")
            print("    Transcription will be disabled.")
            self.speech_client = None

        # --- Porcupine (Wake Word) ---
        try:
            self.porcupine_access_key = os.getenv("PORCUPINE_ACCESS_KEY")
            if not self.porcupine_access_key:
                raise ValueError("PORCUPINE_ACCESS_KEY env var not set.")
            self.porcupine = pvporcupine.create(
                access_key=self.porcupine_access_key,
                keywords=[wake_word] # Built-in keywords: 'gemini', 'porcupine', 'bumblebee', etc.
            )
            self.wake_word_frame_length = self.porcupine.frame_length
            print(f"✅ Porcupine wake word engine initialized for '{wake_word}'.")
        except Exception as e:
            print(f"❌ Porcupine failed to initialize: {e}")
            self.porcupine = None

        # --- WebRTC VAD (Voice Activity Detection) ---
        self.vad = webrtcvad.Vad(3) # Aggressiveness mode 3 is the highest

    async def speak(self, text: str):
        """Use Amazon Polly to speak the given text."""
        if not self.polly:
            print(f"🗣️ (Simulated): {text}")
            # Return a dummy task for simulated speech
            return asyncio.create_task(asyncio.sleep(2))

        print(f"🗣️ Speaking: {text}")
        self.is_speaking = True
        loop = asyncio.get_running_loop()

        # Use standard engine for accessibility mode for potentially clearer, less nuanced speech.
        # Usa o motor 'standard' para o modo de acessibilidade para uma fala potencialmente mais clara e menos sutil.
        engine = 'standard' if self.accessibility_mode else 'neural'

        try:
            # Using an executor to run the blocking I/O in a separate thread
            response = await loop.run_in_executor(None, lambda: self.polly.synthesize_speech(
                Text=text,
                OutputFormat='pcm',
                VoiceId=self.polly_voice,
                Engine=engine,
                SampleRate=str(self.samplerate)
            ))

            audio_stream = response['AudioStream'].read()
            audio_data = np.frombuffer(audio_stream, dtype=np.int16)

            # Play audio non-blockingly
            await loop.run_in_executor(None, sd.play, audio_data, self.samplerate)
            
            async def _wait_for_playback_to_finish():
                await loop.run_in_executor(None, sd.wait)
                self.is_speaking = False

            # Return a task that completes when playback is done
            return asyncio.create_task(_wait_for_playback_to_finish())

        except Exception as e:
            print(f"⚠️ Error during speech synthesis: {e}")
            self.is_speaking = False
            # Return a completed dummy task on error
            return asyncio.create_task(asyncio.sleep(0))

    async def stream_and_speak(self, text_generator):
        """
        Receives text from a generator, synthesizes it into audio chunk by chunk,
        and plays it in real-time.
        """
        if not self.polly:
            # Simulate for environments without AWS
            full_text = ""
            async for text_chunk in text_generator:
                full_text += text_chunk + " "
            print(f"🗣️ (Simulated): {full_text}")
        await asyncio.sleep(5)  # Simulate a long speech
            return

        self.is_speaking = True
        audio_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        playback_finished = asyncio.Event()

        # Use standard engine for accessibility mode.
        # Usa o motor 'standard' para o modo de acessibilidade.
        engine = 'standard' if self.accessibility_mode else 'neural'

        async def producer():
            """Gets text from the generator, synthesizes it, and puts audio in the queue."""
            try:
                async for text_chunk in text_generator:
                    if not self.is_speaking: break  # Stop if interrupted
                    response = await loop.run_in_executor(None, lambda: self.polly.synthesize_speech(
                        Text=text_chunk, OutputFormat='pcm', VoiceId=self.polly_voice,
                        Engine=engine, SampleRate=str(self.samplerate)
                    ))
                    audio_data = np.frombuffer(response['AudioStream'].read(), dtype=np.int16)
                    await audio_queue.put(audio_data)
            except asyncio.CancelledError:
                pass # Expected when interrupted
            finally:
                await audio_queue.put(None) # Signal that production is finished

        def consumer():
            """Consumes audio from the queue and plays it."""
            while self.is_speaking:
                try:
                    audio_data = audio_queue.get_nowait()
                    if audio_data is None: break
                    sd.play(audio_data, self.samplerate)
                    sd.wait()
                except asyncio.QueueEmpty:  # Use get_nowait with a small sleep to yield control
                    await asyncio.sleep(0.01)
                    continue
            sd.stop()  # Ensure sound stops if interrupted
            playback_finished.set()

        producer_task = asyncio.create_task(producer())
        consumer_task = loop.run_in_executor(None, consumer)

        await playback_finished.wait()
        self.is_speaking = False
        producer_task.cancel()
        await asyncio.gather(producer_task, consumer_task, return_exceptions=True)

    async def stop_speaking(self):
        """Forcibly stops any ongoing audio playback."""
        if self.is_speaking:
            print("\n...Stopping playback.")
            self.is_speaking = False  # Signal threads to stop
            await asyncio.get_running_loop().run_in_executor(None, sd.stop)

    def toggle_accessibility_mode(self, enabled: bool) -> str:
        """
        Toggles the emergency accessibility mode.
        Ativa ou desativa o modo de acessibilidade de emergência.
        """
        self.accessibility_mode = enabled
        mode_status = "enabled" if enabled else "disabled"
        print(f"♿ Accessibility Mode has been {mode_status}.")
        return f"Accessibility mode {mode_status}."

    async def wait_for_wake_word(self):
        if not self.porcupine:
            print("Wake word engine not available. Press Enter to activate.")
            await asyncio.get_running_loop().run_in_executor(None, input)
            return

        with sd.InputStream(samplerate=self.porcupine.sample_rate, channels=1, dtype='int16', blocksize=self.porcupine.frame_length) as stream:
            while True:
                pcm, overflowed = stream.read(self.porcupine.frame_length)
                if overflowed:
                    print("⚠️ Audio buffer overflowed while listening for wake word")

                result = self.porcupine.process(pcm.flatten())
                if result >= 0:
                    print("✅ Wake word detected!")
                    return
                await asyncio.sleep(0.01) # yield control

    async def listen_and_transcribe(self) -> str:
        """Records audio from the microphone until silence is detected and transcribes it."""
        if not self.speech_client:
            print("⚠️ Transcription service not available.")
            await asyncio.sleep(5) # Simulate listening
            return "This is a test since transcription is off."
        
        audio_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def callback(indata, frame_count, time_info, status):
            """This is called from a separate audio thread."""
            loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

        async def audio_generator():
            """Pulls audio from the queue and yields it for the Google Speech API."""
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    break
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.samplerate,
            language_code=self.language_code,
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config, interim_results=True
        )

        # Start streaming audio from the microphone
        stream = sd.RawInputStream(
            samplerate=self.samplerate, blocksize=8192, dtype='int16',
            channels=1, callback=callback
        )

        print("...listening for your command, transcribing in real-time.")
        requests = audio_generator()
        api_stream = self.speech_client.streaming_recognize(
            requests=requests,
            config=streaming_config,
        )

        try:
            with stream:
                transcript = await loop.run_in_executor(None, self._process_transcription_stream, api_stream)
                return transcript
        except Exception as e:
            print(f"❌ Primary transcription engine (Google) failed: {e}")
            return ""
        finally:
            # Signal the generator to stop
            await audio_queue.put(None)

    def _process_transcription_stream(self, api_stream) -> str:
        """Processes the streaming response from Google Speech API."""
        final_transcript = ""
        for response in api_stream:
            if not response.results:
                continue

            result = response.results[0]
            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript

            # Display interim results for a responsive feel
            print(f"   » {transcript}\r", end='', flush=True)

            if result.is_final:
                final_transcript = transcript
                # Stop the stream once we have a final result
                api_stream.cancel()
                break
        
        print() # Newline after final result
        return final_transcript