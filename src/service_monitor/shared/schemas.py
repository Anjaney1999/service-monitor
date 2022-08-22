from pydantic import BaseModel

class URL(BaseModel):
    name: str
    url: str