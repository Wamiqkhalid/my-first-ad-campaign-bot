import os
from fastapi import FastAPI, Request, Response, HTTPException
import requests
import uvicorn

app = FastAPI()

# 1. Environment Secrets Setup (We hide these securely inside Render later)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
META_VERIFY_TOKEN = "pakistan_student_bot_secret_2026"
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")

def load_nexaro_store_brain() -> str:
    try:
        with open("knowledge_base.txt", "r") as file:
            return file.read()
    except FileNotFoundError:
        return "Friendly customer representative assistant active."

# 2. Meta Verification Link (The Handshake)
@app.get("/webhook")
async def verify_meta_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == META_VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Token Verification Failed")

# 3. Main Communication Hub Interceptor
@app.post("/webhook")
async def handle_incoming_chats(request: Request):
    payload = await request.json()
    
    if "entry" in payload:
        for entry in payload["entry"]:
            # Route WhatsApp Payloads
            if "changes" in entry:
                for change in entry["changes"]:
                    value = change.get("value", {})
                    if "messages" in value:
                        msg = value["messages"]
                        sender = msg["from"]
                        if msg.get("type") == "text":
                            user_query = msg["text"]["body"]
                            ai_answer = generate_gemini_brain_response(user_query)
                            send_meta_outbound("whatsapp", sender, ai_answer)
                            
            # Route Instagram Messenger Payloads
            elif "messaging" in entry:
                for msg_event in entry["messaging"]:
                    sender = msg_event["sender"]["id"]
                    if "message" in msg_event and "text" in msg_event["message"]:
                        user_query = msg_event["message"]["text"]
                        ai_answer = generate_gemini_brain_response(user_query)
                        send_meta_outbound("instagram", sender, ai_answer)

    return {"status": "success"}

# 4. Process Customer Prompt Through Free Gemini API
def generate_gemini_brain_response(user_text: str) -> str:
    system_rules = load_nexaro_store_brain()
    url = f"https://googleapis.com{GEMINI_API_KEY}"
    
    body = {
        "contents": [{
            "parts": [{"text": f"System Guidelines:\n{system_rules}\n\nCustomer Message: {user_text}"}]
        }]
    }
    
    try:
        res = requests.post(url, json=body, headers={"Content-Type": "application/json"}).json()
        return res['candidates']['content']['parts']['text'].strip()
    except Exception:
        return "Ji ye baat me samajh nahi payi, thoda detail se bata den? Ya ap apna sawal screenshot ki surat me bhej den"

# 5. Push Response Back to Channels (WhatsApp / Instagram)
def send_meta_outbound(channel: str, user_id: str, message_text: str):
    url = "https://facebook.com"
    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}
    
    if channel == "whatsapp":
        data = {"messaging_product": "whatsapp", "to": user_id, "type": "text", "text": {"body": message_text}}
    else:
        data = {"recipient": {"id": user_id}, "message": {"text": message_text}}
        
    requests.post(url, json=data, headers=headers)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
