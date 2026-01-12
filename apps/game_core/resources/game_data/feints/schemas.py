from pydantic import BaseModel


class FeintDTO(BaseModel):
    feint_id: str
    name: str
    description: str
