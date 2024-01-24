from fastapi import FastAPI
from threading import Thread
import uvicorn

app = FastAPI()

@app.get('/')
def main():
  return "Your bot is alive!"

def run():
    uvicorn.run(app=app,host="0.0.0.0", port=8080)

def keep_alive():
    server = Thread(target=run)
    server.start()