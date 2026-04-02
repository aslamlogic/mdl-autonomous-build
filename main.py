from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class EchoRequest(BaseModel):
    text: str

class EchoResponse(BaseModel):
    echo: str

class HealthResponse(BaseModel):
    status: str

class RootResponse(BaseModel):
    message: str = "Welcome to the meta-dev API!"

@app.get("/", response_model=RootResponse)
async def read_root():
    return RootResponse()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy")

@app.post("/echo", response_model=EchoResponse)
async def echo(request: EchoRequest):
    return EchoResponse(echo=request.text)
