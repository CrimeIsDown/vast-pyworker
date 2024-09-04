import dataclasses
import random
import inspect
from typing import Dict, Any

from lib.data_types import ApiPayload, JsonDataException


@dataclasses.dataclass
class InputData(ApiPayload):
    audio_file: str

    @classmethod
    def for_test(cls) -> "InputData":
        audio_file = "misc/samples_jfk.mp3"
        return cls(audio_file=audio_file)

    def generate_payload_json(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    def count_workload(self) -> int:
        # TODO: Actually measure the duration of the audio file
        return 11


    @classmethod
    def from_json_msg(cls, json_msg: Dict[str, Any]) -> "InputData":
        errors = {}
        for param in inspect.signature(cls).parameters:
            if param not in json_msg:
                errors[param] = "missing parameter"
        if errors:
            raise JsonDataException(errors)
        return cls(
            **{
                k: v
                for k, v in json_msg.items()
                if k in inspect.signature(cls).parameters
            }
        )
