"""Entry point for AWS Lambda.

Lambda doesn't run a web server: it calls `handler(event, context)` once per
request, with the HTTP request described as a JSON event. Mangum translates that
event into a normal ASGI request for the FastAPI app, and the response back.
Locally and in Docker we still run uvicorn against app.main:app as before.
"""

from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")  # the app has no startup/shutdown hooks
