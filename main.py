import os
import requests
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException

app = FastAPI()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
META_VERIFY_TOKEN = "pakistan_student_bot_secret_2026"

def load_nexaro_store_brain() -> str:
    try:
        with open("knowledge_base.txt", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Friendly female customer support representative for Nexaro, chatting naturally in Roman Urdu."

@app.get("/webhook")
async def verify_meta_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == META_VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Token Verification Failed")

@app.post("/webhook")
async def handle_incoming_chats(request: Request):
    payload = await request.json()
    if "entry" in payload:
        for entry in payload["entry"]:
            if "changes" in entry:
                for change in entry["changes"]:
                    value = change.get("value", {})
                    if "messages" in value:
                        for msg in value["messages"]:
                            sender_id = msg.get("from")
                            if msg.get("type") == "text":
                                user_query = msg["text"]["body"]
                                ai_answer = generate_gemini_brain_response(user_query)
                                send_meta_outbound("whatsapp", sender_id, ai_answer)
            elif "messaging" in entry:
                for msg_event in entry["messaging"]:
                    sender_id = msg_event.get("sender", {}).get("id")
                    if "message" in msg_event and "text" in msg_event["message"]:
                        if not msg_event["message"].get("is_echo"):
                            user_query = msg_event["message"]["text"]
                            ai_answer = generate_gemini_brain_response(user_query)
                            if "instagram" in entry.get("id", "").lower() or "instagram" in str(msg_event):
                                send_meta_outbound("instagram", sender_id, ai_answer)
                            else:
                                send_meta_outbound("facebook", sender_id, ai_answer)
    return {"status": "success"}

def generate_gemini_brain_response(user_text: str) -> str:
    system_rules = load_nexaro_store_brain()
    url = f"https://googleapis.com{GEMINI_API_KEY}"
    body = {
        "contents": [{
            "parts": [{
                "text": f"System Guidelines:\n{system_rules}\n\nCustomer Message: {user_text}"
            }]
        }]
    }
    try:
        res = requests.post(url, json=body, headers={"Content-Type": "application/json"}).json()
        return res['candidates']['content']['parts']['text'].strip()
    except Exception:
        return "Ji ye baat me samajh nahi payi, thoda detail se bata den? Ya ap apna sawal screenshot ki surat me bhej den."

def send_meta_outbound(platform: str, recipient_id: str, message_text: str):
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    url = "https://facebook.com"
    if platform == "whatsapp":
        data = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {"body": message_text}
        }
    else:
        data = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
    requests.post(url, json=data, headers=headers)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
