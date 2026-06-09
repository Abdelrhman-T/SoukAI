from fastapi import FastAPI

from routes.api import base_router, nlp_router

app = FastAPI()

app.include_router(base_router)
app.include_router(nlp_router)
