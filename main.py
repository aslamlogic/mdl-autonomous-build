from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the meta-dev API!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}