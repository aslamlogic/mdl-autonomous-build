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
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"status": "meta system running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run():
    try:
        from iteration.controller import main
        main()
        return {"status": "iteration started"}
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e)
        }
