"""OpsGate FastAPI server — thin wrapper that holds a single env instance."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from server.opsgate_environment import OpsGateEnvironment
from models import ToolCall

app = FastAPI(title="OpsGate Environment API")
env = OpsGateEnvironment()


class StepRequest(BaseModel):
    action: dict


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/reset")
def reset():
    obs = env.reset()
    return {"observation": obs.model_dump(), "reward": 0.0, "done": False}


@app.post("/step")
def step(req: StepRequest):
    action = ToolCall(**req.action)
    obs = env.step(action)
    return {
        "observation": obs.model_dump(),
        "reward": obs.reward,
        "done": obs.done,
    }


@app.get("/state")
def state():
    s = env.state
    if s is None:
        return {"error": "No active episode. Call /reset first."}
    return s.model_dump()
