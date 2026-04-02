from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to the meta-dev API!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

class EchoRequest(BaseModel):
    text: str

@app.post("/echo")
async def echo(request: EchoRequest):
    return {"echo": request.text}
