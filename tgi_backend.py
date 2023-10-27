import requests
from flask import Response
import time

from server_metrics import LLMServerMetrics
from generic_backend import Backend

MODEL_SERVER = '127.0.0.1:5001'

class TGIBackend(Backend):
    def __init__(self, container_id, control_server_url, master_token, send_data):
        super().__init__(container_id=container_id, control_server_url=control_server_url, master_token=master_token, send_data=send_data)
        self.metrics = LLMServerMetrics(id=container_id, control_server_url=control_server_url, master_token=master_token, send_data=send_data)
        self.model_server_addr = MODEL_SERVER

    def hf_tgi_wrapper(self, inputs, parameters):
        hf_prompt = {"inputs" : inputs, "parameters" : parameters}
        self.metrics.start_req(text_prompt=inputs, parameters=parameters)
        try:
            response = requests.post(f"http://{self.model_server_addr}/generate_stream", json=hf_prompt, stream=True)
            if response.status_code == 200:
                for byte_payload in response.iter_lines():
                    yield byte_payload
                    yield "\n"
            self.metrics.finish_req(text_prompt=inputs, parameters=parameters)
        
        except requests.exceptions.RequestException as e:
            print(f"[TGI-backend] Request error: {e}")

    def generate_stream(self, model_request):
        return Response(self.hf_tgi_wrapper(model_request["inputs"], model_request["parameters"]))


    def health_handler(self):
        try:
            response = requests.get(f"http://{self.model_server_addr}/health")
            print(f"health response: {response.status_code}")
            if response.status_code == 200:
                return 200, "" 
            
            return response.status_code, None
        
        except requests.exceptions.RequestException as e:
            print(f"[TGI-backend] Request error: {e}")

        return 500, None 

    def info_handler(self):
        try:
            response = requests.get(f"http://{self.model_server_addr}/info")
            print(f"info response: {response.status_code}")
            if response.status_code == 200:
                return 200, response.content 
            
            return response.status_code, None
        
        except requests.exceptions.RequestException as e:
            print(f"[TGI-backend] Request error: {e}")

        return 500, None 

    def metrics_handler(self):
        try:
            response = requests.get(f"http://{self.model_server_addr}/metrics")
            print(f"metrics response: {response.status_code}")
            if response.status_code == 200:
                return 200, response.content
            
            return response.status_code, None
        
        except requests.exceptions.RequestException as e:
            print(f"[TGI-backend] Request error: {e}")

        return 500, None 
