import asyncio
import threading
import logging
import os
import time
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from pydub import AudioSegment

class TelegramManager:
    def __init__(self, logger):
        self.logger = logger
        self.application = None
        self.callbacks = []
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.start_loop, daemon=True)
        self.thread.start()
        self.connected = False

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def register_callback(self, callback):
        """Callback signature: (type: str, content: str, chat_id: str)"""
        self.callbacks.append(callback)

    def connect(self, token):
        asyncio.run_coroutine_threadsafe(self._connect(token), self.loop)

    async def _connect(self, token):
        try:
            if self.application:
                await self.application.stop()
                await self.application.shutdown()

            self.application = Application.builder().token(token).build()
            
            # Handlers
            self.application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, self._handle_audio))
            self.application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self._handle_text))

            await self.application.initialize()
            await self.application.start()
            # Start polling in a way that doesn't block the loop forever here
            self.loop.create_task(self.application.updater.start_polling())
            
            self.logger.info(f"Telegram Bot connected")
            self.connected = True
        except Exception as e:
            self.logger.error(f"Telegram connection error: {e}")
            self.connected = False

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text: return
        chat_id = str(update.message.chat_id)
        text = update.message.text
        self.logger.info(f"Telegram received text from {chat_id}: {text}")
        for cb in self.callbacks:
            try: cb("text", text, chat_id)
            except: pass

    async def _handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message: return
        
        # Determine if voice or audio file
        audio_obj = update.message.voice or update.message.audio
        if not audio_obj: return

        chat_id = str(update.message.chat_id)
        self.logger.info(f"Telegram received audio from {chat_id}")

        try:
            os.makedirs("downloads", exist_ok=True)
            # Download file
            new_file = await context.bot.get_file(audio_obj.file_id)
            
            ext = ".ogg" if update.message.voice else os.path.splitext(audio_obj.file_name or "audio.mp3")[1]
            temp_path = os.path.join("downloads", f"tg_temp_{int(time.time())}{ext}")
            
            await new_file.download_to_drive(temp_path)
            
            # Convert to WAV for ComfyUI
            wav_path = os.path.join("downloads", f"tg_audio_{int(time.time())}.wav")
            
            try:
                audio = AudioSegment.from_file(temp_path)
                audio.export(wav_path, format="wav")
                self.logger.info(f"Converted Telegram audio to {wav_path}")
                
                # Cleanup temp
                try: os.remove(temp_path)
                except: pass

                if os.path.exists(wav_path):
                    for cb in self.callbacks:
                        try: cb("audio", os.path.abspath(wav_path), chat_id)
                        except: pass
            except Exception as e:
                self.logger.error(f"Failed to convert Telegram audio: {e}")

        except Exception as e:
            self.logger.error(f"Failed to process Telegram audio: {e}")

    def send_text(self, chat_id, text):
        if not self.connected or not self.application: return
        asyncio.run_coroutine_threadsafe(
            self.application.bot.send_message(chat_id=chat_id, text=text),
            self.loop
        )

    def stop(self):
        if self.application:
            asyncio.run_coroutine_threadsafe(self.application.stop(), self.loop)
        self.loop.stop()
