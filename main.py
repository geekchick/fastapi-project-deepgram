from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocketState
from typing import Dict, Callable, List
from dotenv import load_dotenv
from deepgram import Deepgram

import os
import re

KEYWORDS = {
                "michael jordan": "red",
                "flu": "green"
            }

load_dotenv()

app = FastAPI()

dg_client = Deepgram(os.getenv('DEEPGRAM_API_KEY'))

templates = Jinja2Templates(directory="templates")


def format_string(matchobj) -> str:
    matched_string = matchobj.group(0)
    color = KEYWORDS.get(matched_string.lower())
    return r'<span style="background-color: {}">{}</span>'.format(color, matched_string)

def format_transcript_helper(transcript, keywords) -> str:
    terms = "|".join(keywords.keys())
    test_search = r"({})".format(terms)
    formatted_transcript = re.sub(test_search, format_string, transcript, flags=re.IGNORECASE)

    return formatted_transcript

async def process_audio(fast_socket: WebSocket):
    async def get_transcript(data: Dict) -> None:
        if 'channel' in data:
            transcript = data['channel']['alternatives'][0]['transcript']
        
            if transcript:
                formatted_transcript = format_transcript_helper(transcript, KEYWORDS) 

                await fast_socket.send_text(formatted_transcript)

    deepgram_socket = await connect_to_deepgram(get_transcript)

    while fast_socket.application_state == WebSocketState.CONNECTED:
        data = await fast_socket.receive_bytes()
        deepgram_socket.send(data)

async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None]) -> str:
    def on_connection_closed(exit_code: int) -> int:
        exit(0)

    try:
        socket = await dg_client.transcription.live({'punctuate': True, 'interim_results': False})
        socket.registerHandler(socket.event.CLOSE, on_connection_closed)
        socket.registerHandler(socket.event.TRANSCRIPT_RECEIVED, transcript_received_handler)

        return socket
    except Exception as e:
        raise Exception(f'Could not open socket: {e}')

@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    return templates.TemplateResponse("players.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await process_audio(websocket)
    await websocket.close()
