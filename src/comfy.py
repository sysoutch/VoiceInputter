import json
import os
import requests
import websocket
import wave
import numpy as np
from .config import COMFY_URL, WORKFLOW_FILE, INPUT_FILENAME

class ComfyClient:
    def __init__(self, logger, client_id):
        self.logger = logger
        self.client_id = client_id
        self.workflow = self.load_workflow()

    def load_workflow(self):
        try:
            with open(WORKFLOW_FILE, 'r', encoding='utf-8') as f:
                wf = json.load(f)
            self.logger.info(f"Loaded workflow from {WORKFLOW_FILE}")
            return wf
        except Exception as e:
            self.logger.error(f"Failed to load workflow file: {e}")
            return {}

    def save_audio(self, audio_data, sample_rate):
        if not audio_data: return False
        audio_array = np.concatenate(audio_data, axis=0)
        audio_int16 = (audio_array * 32767).astype(np.int16)
        with wave.open(INPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())
        return True

    def upload_audio(self):
        try:
            with open(INPUT_FILENAME, 'rb') as f:
                files = {"image": (INPUT_FILENAME, f), "overwrite": (None, "true")}
                requests.post(f"http://{COMFY_URL}/upload/image", files=files, timeout=5)
            return True
        except Exception as e:
            self.logger.error(f"Failed to upload audio: {e}")
            return False

    def find_node(self, key, value):
        for node_id, node in self.workflow.items():
            if key == "class_type" and node.get("class_type") == value: return node_id
            if key == "title" and node.get("_meta", {}).get("title") == value: return node_id
        return None

    def process(self, audio_data, sample_rate):
        if not self.save_audio(audio_data, sample_rate):
            return None
        
        abs_path = os.path.abspath(INPUT_FILENAME)
        load_node_id = self.find_node("class_type", "LoadAudio")
        if load_node_id:
            self.workflow[load_node_id]["inputs"]["audio"] = abs_path

        whisper_node_id = self.find_node("class_type", "Apply Whisper")
        preview_text_node_id = self.find_node("title", "Preview Text")
        if not whisper_node_id: whisper_node_id = "98"

        ws = None
        final_text = ""
        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{COMFY_URL}/ws?clientId={self.client_id}")
            
            prompt_payload = {"prompt": self.workflow, "client_id": self.client_id}
            resp = requests.post(f"http://{COMFY_URL}/prompt", json=prompt_payload)
            prompt_id = resp.json().get("prompt_id")
            
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executed':
                        data = message['data']
                        if data['prompt_id'] == prompt_id:
                            node_id = data.get('node')
                            is_target = False
                            if preview_text_node_id and node_id == preview_text_node_id: is_target = True
                            elif not preview_text_node_id and node_id == whisper_node_id: is_target = True
                            
                            if is_target:
                                output = data.get('output', {})
                                if isinstance(output, dict):
                                    if 'string' in output: final_text = output['string']
                                    elif 'text' in output: final_text = output['text']
                                    elif 'ui' in output and 'text' in output['ui']: final_text = output['ui']['text'][0]
                                    else:
                                        for v in output.values():
                                            if isinstance(v, list) and len(v)>0 and isinstance(v[0], str) and not v[0].endswith('.wav'):
                                                final_text = v[0]
                                                break
                                if isinstance(final_text, list): final_text = final_text[0]
                                if final_text: break

                    if message['type'] == 'executing' and message['data']['node'] is None:
                        if message['data']['prompt_id'] == prompt_id: break
        except Exception as e:
            self.logger.error(f"ComfyUI Process Error: {e}")
        finally:
            if ws: ws.close()
            
        return final_text
