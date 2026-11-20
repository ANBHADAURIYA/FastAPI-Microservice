from pydantic import BaseModel


class SummaryRequest(BaseModel):
    # Emptiness and max length are checked in the route (max length is a
    # runtime setting), both returning 400 as the spec requires.
    text: str


class SummaryResponse(BaseModel):
    summary: str
