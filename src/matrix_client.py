import asyncio
import threading
import logging
import os
import time
from nio import AsyncClient, UploadResponse, DownloadResponse
from nio.events.room_events import RoomMessageText, RoomMessageAudio

class MatrixManager:
    def __init__(self, logger, name="Matrix"):
        self.logger = logger
        self.name = name
        self.client = None
        self.callbacks = []
        self.sync_task = None
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.start_loop, daemon=True)
        self.thread.start()
        self.connected = False

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def register_callback(self, callback):
        """Callback signature: (type: str, content: str, room_id: str)"""
        self.callbacks.append(callback)

    def connect(self, homeserver, user_id, token):
        future = asyncio.run_coroutine_threadsafe(self._connect(homeserver, user_id, token), self.loop)
        return future # Could wait for result if needed

    async def _connect(self, homeserver, user_id, token):
        try:
            if self.client:
                await self.client.close()
            
            if self.sync_task:
                self.sync_task.cancel()
                self.sync_task = None
            
            self.client = AsyncClient(homeserver, user_id)
            self.client.access_token = token
            self.client.user_id = user_id # Explicitly set
            
            # Simple check
            resp = await self.client.sync(timeout=1000, full_state=True)
            if hasattr(resp, 'next_batch'):
                self.logger.info(f"[{self.name}] Matrix connected as {user_id}")
                self.connected = True
                
                # Start Sync Loop
                self.sync_task = self.loop.create_task(self._sync_forever())
            else:
                self.logger.error(f"[{self.name}] Matrix sync failed: {resp}")
                self.connected = False
        except Exception as e:
            self.logger.error(f"[{self.name}] Matrix connection error: {e}")
            self.connected = False

    async def _sync_forever(self):
        try:
            self.client.add_event_callback(self._on_text, RoomMessageText)
            self.client.add_event_callback(self._on_audio, RoomMessageAudio)
            await self.client.sync_forever(timeout=30000)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Matrix sync loop error: {e}")

    async def _on_text(self, room, event):
        if not self.callbacks: return
        
        self.logger.info(f"[{self.name}] Matrix received text from {event.sender}: {event.body}")
        for cb in self.callbacks:
            try: cb("text", event.body, room.room_id)
            except: pass

    async def _on_audio(self, room, event):
        if event.sender == self.client.user_id: return
        if not self.callbacks: return
        
        self.logger.info(f"[{self.name}] Matrix received audio from {event.sender}")
        
        url = getattr(event, 'url', None) 
        if not url and 'url' in event.source.get('content', {}):
            url = event.source['content']['url']
            
        if url:
            try:
                os.makedirs("downloads", exist_ok=True)
                # Use simplified filename to avoid issues with special chars in event_id
                safe_name = f"audio_{int(time.time())}_{event.event_id[-8:]}.wav"
                filename = os.path.join("downloads", safe_name)
                abs_path = os.path.abspath(filename)
                
                # matrix-nio download to memory to ensure we have data
                resp = await self.client.download(mxc=url)
                
                if isinstance(resp, DownloadResponse):
                    data = resp.body
                    self.logger.info(f"Downloaded audio data: {len(data)} bytes")
                    
                    if data:
                        try:
                            with open(abs_path, "wb") as f:
                                f.write(data)
                            
                            self.logger.info(f"Saved audio to {abs_path}")
                            
                            if os.path.exists(abs_path):
                                for cb in self.callbacks:
                                    try: cb("audio", abs_path, room.room_id)
                                    except: pass
                            else:
                                self.logger.error(f"File write reported success but file missing at {abs_path}")
                        except Exception as e:
                            self.logger.error(f"Failed to write file to disk: {e}")
                    else:
                        self.logger.error("Downloaded audio data is empty")
                else:
                    self.logger.error(f"Failed to download audio (Response): {resp}")
                    
            except Exception as e:
                self.logger.error(f"Failed to download audio (Exception): {e}")

    def send_text(self, room_id, text):
        if not self.connected or not self.client: return
        asyncio.run_coroutine_threadsafe(
            self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": text}
            ),
            self.loop
        )

    def send_audio(self, room_id, filename):
        if not self.connected or not self.client:
            self.logger.error("Matrix not connected")
            return
        asyncio.run_coroutine_threadsafe(self._upload_and_send(room_id, filename), self.loop)

    async def _upload_and_send(self, room_id, filename):
        try:
            mime_type = "audio/wav"
            file_size = os.path.getsize(filename)
            
            with open(filename, "rb") as f:
                resp, maybe_keys = await self.client.upload(
                    f,
                    content_type=mime_type,
                    filename=os.path.basename(filename),
                    filesize=file_size
                )
            
            if isinstance(resp, UploadResponse):
                content_uri = resp.content_uri
                
                content = {
                    "body": os.path.basename(filename),
                    "info": {
                        "size": file_size,
                        "mimetype": mime_type,
                    },
                    "msgtype": "m.audio",
                    "url": content_uri
                }
                
                await self.client.room_send(
                    room_id=room_id,
                    message_type="m.room.message",
                    content=content
                )
                self.logger.info(f"[{self.name}] Matrix audio sent to {room_id}")
            else:
                self.logger.error(f"[{self.name}] Matrix upload failed: {resp}")

        except Exception as e:
            self.logger.error(f"[{self.name}] Matrix send error: {e}")

    def stop(self):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)
        self.loop.stop()
