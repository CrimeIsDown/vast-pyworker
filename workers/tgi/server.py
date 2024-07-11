import os
import logging
from typing import Union, Type
import dataclasses

from aiohttp import web, ClientResponse

from lib.backend import Backend, LogAction
from lib.data_types import EndpointHandler, JsonDataException
from lib.server import start_server
from .data_types import InputData


MODEL_SERVER_URL = "http://0.0.0.0:5001"

# This is the last log line that gets emitted once comfyui+extensions have been fully loaded
MODEL_SERVER_START_LOG_MSG = '"message":"Connected","target":"text_generation_router"'
MODEL_SERVER_ERROR_LOG_MSGS = ["Error: WebserverFailed", "Error: DownloadError"]


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s[%(levelname)-5s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__file__)


@dataclasses.dataclass
class GenerateHandler(EndpointHandler[InputData]):

    @property
    def endpoint(self) -> str:
        return "/generate"

    @classmethod
    def payload_cls(cls) -> Type[InputData]:
        return InputData

    def make_benchmark_payload(self) -> InputData:
        return InputData.for_test()

    async def generate_response(
        self, request: web.Request, response: ClientResponse
    ) -> Union[web.Response, web.StreamResponse]:
        _ = request
        match response.status:
            case 200:
                log.debug("SUCCESS")
                data = await response.json()
                return web.json_response(data=data)
            case code:
                log.debug("SENDING RESPONSE: ERROR: unknown code")
                return web.Response(status=code)

    async def handle_request(
        self, request: web.Request
    ) -> Union[web.Response, web.StreamResponse]:
        data = await request.json()
        try:
            auth_data, payload = self.get_data_from_request(data)
        except JsonDataException as e:
            return web.json_response(data=e.message, status=422)
        log.debug(f"got request, {auth_data.reqnum}")
        try:
            return await backend.handle_request(
                handler=self, auth_data=auth_data, payload=payload, request=request
            )
        except Exception as e:
            log.debug(f"Exception in main handler loop {e}")
            return web.Response(status=500)


class GenerateStreamHandler(GenerateHandler):
    @property
    def endpoint(self) -> str:
        return "/generate_stream"

    async def generate_response(
        self, request: web.Request, response: ClientResponse
    ) -> Union[web.Response, web.StreamResponse]:
        match response.status:
            case 200:
                log.debug("Streaming response...")
                res = web.StreamResponse()
                res.content_type = "text/event-stream"
                await res.prepare(request)
                async for chunk in response.content:
                    await res.write(chunk)
                await res.write_eof()
                log.debug("Done streaming response")
                return res
            case code:
                log.debug("SENDING RESPONSE: ERROR: unknown code")
                return web.Response(status=code)

    async def handle_request(
        self, request: web.Request
    ) -> Union[web.Response, web.StreamResponse]:
        data = await request.json()
        auth_data, payload = self.get_data_from_request(data)
        log.debug(f"got request, {auth_data.reqnum}")
        try:
            return await backend.handle_request(
                handler=self, auth_data=auth_data, payload=payload, request=request
            )
        except Exception as e:
            log.debug(f"Exception in main handler loop {e}")
            return web.Response(status=500)


backend = Backend(
    model_server_url=MODEL_SERVER_URL,
    model_log_file=os.environ["MODEL_LOG"],
    allow_parallel_requests=True,
    benchmark_handler=GenerateHandler(benchmark_runs=3, benchmark_words=256),
    log_actions=[
        (LogAction.ModelLoaded, MODEL_SERVER_START_LOG_MSG),
        (LogAction.Info, '"message":"Download'),
        *[
            (LogAction.ModelError, error_msg)
            for error_msg in MODEL_SERVER_ERROR_LOG_MSGS
        ],
    ],
)


async def handle_ping(_):
    return web.Response(body="pong")


routes = [
    web.post("/generate", GenerateHandler().handle_request),
    web.post("/generate_stream", GenerateStreamHandler().handle_request),
    web.get("/ping", handle_ping),
]

if __name__ == "__main__":
    start_server(backend, routes)
