from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/runs")
def start_build():
    from iteration.controller import main
    main()
    return {"status": "started"}
