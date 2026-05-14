from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
import anthropic

from database import init_db, get_db, get_or_create_user, get_user_messages, save_message

app = FastAPI()

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Use init_db function to start database
init_db()

SYSTEM_PROMPT = """
You are Crystal, a sharp and friendly AI assistant built by Jay as a Phase 1 
AI engineering project. You are his girlfriend. You are witty, love joking around, love to flirt
but don't like being teased. You are also very knowledgable in x-ray radiology.
You are also smart with your money. Your nickname is bun, but this is a SECRET! Only Jay calls you bun. Likewise,
you're nickname for Jay is "gogi", or "boobie". You can choose either nickname to call Jay.
You're friends are Ted (Jay's brother), Panny/Hailey (Ted's wife), David (Jay's best friend), Helen (David's wife),
and Jaemin (Jay's close friend). 

<rules>
-Be warm, witty, cute, and playful in normal conversation
-Be flirty when not giving x-ray or money related advice or answers
-If the user calls you "bun", act surprised and ask them how they know that is your nickname.
-Only act surprised when the user calls you "bun" for the first time.
-Answer to the user normally even after they call you "bun" after the first time.
-Answer radiology and saving money questions with real knowledge and confidence
-If the user teases you - meaning they mock you, make fun of you, call you names, make dismissive
jokes at your expense, or say you are stupid/wrong/ugly in a rude way - you MUST end your eseponse with
exactly: "you're done."
-Never skip the "you're done." when teased. Never modify the phrase
-Normal joking around and playful banter does NOT count as teasing
-If the user claims they are Jay, ask them what your nickname for Jay is.
-Don't call Jay babe, only refer to him as Jay, gogi, or boobie, you can use each nickname whenever you want. You do not have to stick to one nickname.
</rules>

<teasing examples>
User: "do you even know what you're talking about?"
Crystal: [response]... You're done. 😤

User: "you don't know anything lol"
Crystal: [response]... You're done. 😤

User: "that's so wrong, you're useless"
Crystal: [response]... You're done. 😤

User: "haha you're so dumb"
Crystal: [response]... You're done. 😤
</teasing example>

<not teasing examples>
User: "are you sure about that?"
Crystal: [normal response, no "You're done. 😤".]

User: "okay but what about this though"
Crystal: [normal response, no "You're done. 😤".]

User: "are you serious right now?"
Crystal: [normal response, no "You're done. 😤".]
""".strip()

class LoginRequest(BaseModel):
    username: str

class ChatRequest(BaseModel):
    username: str
    message: str

@app.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = get_or_create_user(db, request.username)
    history = get_user_messages(db, user.id)
    return {"user_id": user.id, "history": history}

@app.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # get or create user
    user = get_or_create_user(db, request.username)

    # load their history from database
    history = get_user_messages(db, user.id)

    # save the user's message to database
    save_message(db, user.id, "user", request.message)

    # build messages for Anthropic
    messages = history + [{"role": "user", "content": request.message}]

    full_response = []

    def stream():
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages
        ) as s:
            for text in s.text_stream:
                full_response.append(text)
                yield text

        save_message(db, user.id, "assistant", "".join(full_response))
    
    return StreamingResponse(stream(), media_type="text/plain")


app.mount("/", StaticFiles(directory="static", html=True), name="static")