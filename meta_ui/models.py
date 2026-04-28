from pydantic import BaseModel
from typing import Any, Dict, Optional

class RunCommand(BaseModel):
    instruction: str
    payload: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class RunResult(BaseModel):
    status: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
