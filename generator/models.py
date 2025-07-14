from pydantic import BaseModel, Field, RootModel
from typing import Union, Dict

class GeneratorPayload(RootModel[Dict[str, Union[int, float, str]]]):
    pass


class GeneratorDataModel(BaseModel):
    timestamp: int = Field(..., ge=0, description="Unix timestamp in milliseconds")
    payload: GeneratorPayload

    def model_dump(self, *args, **kwargs):
        base = super().model_dump(*args, **kwargs)
        return {
            "timestamp": base["timestamp"],
            **base["payload"]
        }

    @classmethod
    def from_flat_dict(cls, data: Dict[Union[int, str], Union[int, float, str]]):
        ts = data.pop("timestamp", None)
        return cls(timestamp=ts, payload=GeneratorPayload(data))