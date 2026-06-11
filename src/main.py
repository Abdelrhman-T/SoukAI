from fastapi import FastAPI

from routes.agent import agent_router
from routes.api import base_router, nlp_router

app = FastAPI()

app.include_router(base_router)
app.include_router(nlp_router)
app.include_router(agent_router)
