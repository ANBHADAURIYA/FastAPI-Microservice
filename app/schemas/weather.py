from pydantic import BaseModel


class WeatherResponse(BaseModel):
    city: str
    temperature: float  # degrees Celsius
    condition: str
    humidity: int  # percent
