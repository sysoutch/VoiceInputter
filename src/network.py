import threading
import socket
import json
import time
import http.server
import socketserver
import requests
import logging
import io
import wave
import numpy as np
from .config import SAMPLE_RATE

PORT = 5000
DISCOVERY_PORT = 5001
DISCOVERY_MSG = b"VOICE_INPUTTER_DISCOVERY"

class NetworkManager:
    def __init__(self, comfy_client, logger):
        self.comfy = comfy_client
        self.logger = logger
        self.peers = {} # ip -> last_seen
        self.server_thread = None
        self.discovery_thread = None
        self.running = False
        
        # Determine local IP
        self.local_ip = self.get_local_ip()

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def start(self):
        self.running = True
        self.start_server()
        self.start_discovery()

    def stop(self):
        self.running = False
        # Server stop is tricky with socketserver, usually shutdown()
        if self.httpd: self.httpd.shutdown()

    # --- HTTP Server ---
    def start_server(self):
        handler = RequestHandlerFactory(self.comfy, self.logger)
        self.httpd = ThreadedHTTPServer(("0.0.0.0", PORT), handler)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()
        self.logger.info(f"Network Server started on {self.local_ip}:{PORT}")

    # --- Discovery ---
    def start_discovery(self):
        self.discovery_thread = threading.Thread(target=self.discovery_loop, daemon=True)
        self.discovery_thread.start()

    def discovery_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", DISCOVERY_PORT))
        sock.settimeout(2.0)

        last_broadcast = 0
        
        while self.running:
            # Broadcast existence
            if time.time() - last_broadcast > 5.0:
                try:
                    msg = json.dumps({"ip": self.local_ip, "port": PORT}).encode()
                    sock.sendto(msg, ("<broadcast>", DISCOVERY_PORT))
                    last_broadcast = time.time()
                except Exception as e:
                    pass # Network might be down

            # Listen for others
            try:
                data, addr = sock.recvfrom(1024)
                if addr[0] == self.local_ip: continue # Ignore self
                
                try:
                    info = json.loads(data.decode())
                    self.peers[info['ip']] = time.time()
                except: pass
            except socket.timeout:
                pass
            
            # Cleanup old peers (30s timeout)
            now = time.time()
            self.peers = {ip: t for ip, t in self.peers.items() if now - t < 30}

    # --- Client ---
    def get_peers(self):
        return list(self.peers.keys())

    def send_audio_file(self, target_ip, filename):
        try:
            url = f"http://{target_ip}:{PORT}/transcribe"
            with open(filename, 'rb') as f:
                files = {"file": ("audio.wav", f, "audio/wav")}
                resp = requests.post(url, files=files, timeout=30)
            
            if resp.status_code == 200:
                return resp.text
            else:
                self.logger.error(f"Network error: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            self.logger.error(f"Network send error: {e}")
            return None

    def send_audio(self, target_ip, audio_data):
        # Convert audio_data (list of numpy arrays) to bytes
        try:
            audio_array = np.concatenate(audio_data, axis=0)
            audio_int16 = (audio_array * 32767).astype(np.int16)
            
            # Create WAV in memory
            bio = io.BytesIO()
            with wave.open(bio, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_int16.tobytes())
            bio.seek(0)
            
            # Post
            url = f"http://{target_ip}:{PORT}/transcribe"
            files = {"file": ("audio.wav", bio, "audio/wav")}
            resp = requests.post(url, files=files, timeout=30)
            
            if resp.status_code == 200:
                return resp.text
            else:
                return None
        except Exception as e:
            self.logger.error(f"Network send error: {e}")
            return None

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

def RequestHandlerFactory(comfy_client, logger):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path == '/transcribe':
                try:
                    # Parse Multipart
                    # Minimal parser or use cgi? cgi is deprecated.
                    # We can cheat and just read the body if we assume simple upload.
                    # But requests sends multipart.
                    # Let's try to find boundary.
                    content_type = self.headers['Content-Type']
                    if 'multipart/form-data' not in content_type:
                        self.send_error(400, "Bad Content-Type")
                        return
                    
                    length = int(self.headers['Content-Length'])
                    body = self.rfile.read(length)
                    
                    # Extract file content (Quick and dirty multipart parsing)
                    boundary = content_type.split("boundary=")[1].encode()
                    parts = body.split(boundary)
                    # Loop parts to find the file
                    audio_bytes = None
                    for part in parts:
                        if b"filename=" in part:
                            # This is the file
                            # Find start of content (double newline)
                            header_end = part.find(b"\r\n\r\n")
                            if header_end != -1:
                                content = part[header_end+4:]
                                # Remove trailing \r\n--
                                content = content.rstrip(b"\r\n--")
                                audio_bytes = content
                                break
                    
                    if not audio_bytes:
                        self.send_error(400, "No file found")
                        return

                    # Save to file expected by ComfyClient
                    # We need to hack ComfyClient to accept file path or we save to 'input_audio.wav'
                    # ComfyClient uses INPUT_FILENAME global.
                    # We should probably lock this if multiple requests come in?
                    # For now, just write it.
                    from .config import INPUT_FILENAME
                    with open(INPUT_FILENAME, 'wb') as f:
                        f.write(audio_bytes)
                    
                    # Process
                    # We need to bypass ComfyClient.save_audio and go straight to upload/process
                    # But ComfyClient.process takes audio_data (numpy).
                    # We should modify ComfyClient to accept 'skip_save=True'?
                    # Or we just use ComfyClient.upload_audio() + logic.
                    
                    # Wait, ComfyClient.process(audio_data) does: save_audio -> upload -> websocket.
                    # We already saved the file.
                    # So we can pass audio_data=None to process?
                    # ComfyClient.process needs modification to handle "File already exists".
                    
                    # Let's Modify ComfyClient later. For now, assume we can call process(None) if we tweak it.
                    # Or simpler: Trigger process with dummy data? No, save_audio checks data.
                    
                    # I will modify ComfyClient to check if audio_data is None, then skip save.
                    text = comfy_client.process(None, SAMPLE_RATE)
                    
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(text.encode() if text else b"")
                    
                except Exception as e:
                    logger.error(f"Server error: {e}")
                    self.send_error(500)
            else:
                self.send_error(404)
                
        def log_message(self, format, *args):
            return # Suppress default logging
            
    return Handler
