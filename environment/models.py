from pydantic import BaseModel, Field
from datetime import datetime

class EnvironmentData(BaseModel):
    pm1_0: int = Field(..., alias='pm1_0(ug/m3)')
    pm2_5: int = Field(..., alias='pm2_5(ug/m3)')
    pm10_0: int = Field(..., alias='pm10_0(ug/m3)')
    humidity: float = Field(..., alias='hum(%)')
    temp_1: float = Field(..., alias='temp_1(*C)')
    dew_point: float = Field(..., alias='dp(*C)')
    timestamp: datetime

    class Config:
        validate_by_name = True