from ast import Bytes
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocketState
from typing import Dict, Callable, List
from dotenv import load_dotenv
from deepgram import Deepgram

import os
import re

from main_old import connect_to_deepgram

load_dotenv()

app = FastAPI()

dg_client = Deepgram(os.getenv('DEEPGRAM_API_KEY'))

templates = Jinja2Templates(directory="templates")


async def process_audio(connection: WebSocket, data: dict) -> WebSocket:
    if 'channel' in data:
        transcript = data['channel']['alternatives'][0]['transcript']
    
        if transcript:
            await connection.send_text(transcript)

        return connection


async def connect_to_deepgram() -> WebSocket:
    def on_connection_closed(exit_code: int) -> int:
        exit(0)

    try:
        deepgram_socket = await dg_client.transcription.live({'punctuate': True, 'interim_results': False})
        deepgram_socket.registerHandler(deepgram_socket.event.CLOSE, on_connection_closed)
        deepgram_socket.registerHandler(deepgram_socket.event.TRANSCRIPT_RECEIVED, print)

        return deepgram_socket

    except Exception as e:
        raise Exception(f'Could not open socket: {e}')



@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    return templates.TemplateResponse("players.html", {"request": request})

@app.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket): # websocket that connects the client and server
    await websocket.accept()

    while True:
        data = await websocket.receive_bytes() # while True receive bytes
        deepgram_connection = await connect_to_deepgram() # connect to deepgram
        await process_audio(deepgram_connection, data) # then process the audio
 
