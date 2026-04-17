"""Pydantic Schemas"""
from typing import Annotated
from pydantic import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(lambda v: str(v))]
