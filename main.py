from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class RootResponse(BaseModel):
    message: str = "Welcome to the meta-dev API!"

class HealthResponse(BaseModel):
    status: str = "healthy"

class EchoRequest(BaseModel):
    text: str = "hello"

class EchoResponse(BaseModel):
    echo: str = "hello"

@app.get("/", response_model=RootResponse)
async def root():
    return RootResponse()

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()

@app.post("/echo", response_model=EchoResponse)
async def echo(request: EchoRequest):
    return EchoResponse(echo=request.text)