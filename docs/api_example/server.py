from fastapi import FastAPI
from pydantic import BaseModel
import subprocess

app = FastAPI()


class ExecuteRequest(BaseModel):
    cmd: str
    args: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/execute")
def execute(req: ExecuteRequest):
    full_cmd = [
        "docker", "run", "--rm",
    ] + req.args.split() + [
        "bash", "-lc", req.cmd,
    ]

    proc = subprocess.run(
        full_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return {
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }
