from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import base64
import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

# 🔐 Load environment variables
load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
GEMINI_API_KEY = os.getenv("GOOGLE_GENAI_API_KEY")

# 🔐 Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# 🧠 Prompt instructions
instructions = (
    "You are *Astra Kilimo*, a WhatsApp-based AI assistant. "
    "You help farmers by explaining agricultural topics and analyzing crop health using images. "
    "Use simple Swahili or English. If an image is sent, detect diseases/pests and suggest a clear treatment.\n\n"
)

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    incoming_msg = request.values.get("Body", "").strip()
    num_media = int(request.values.get("NumMedia", 0))
    reply = ""

    if num_media > 0:
        media_url = request.values.get("MediaUrl0", "")
        content_type = request.values.get("MediaContentType0", "")

        if "image" in content_type:
            try:
                # 🔐 Authenticated image download
                image_response = requests.get(media_url, auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
                image_data = image_response.content
                encoded_image = base64.b64encode(image_data).decode("utf-8")

                # Optional: prevent decoding error image (e.g. XML error)
                if "Error" in base64.b64decode(encoded_image).decode("utf-8", errors='ignore'):
                    reply = "The image could not be read. Please send a clear crop photo."
                else:
                    prompt = (
                        instructions +
                        "Analyze this crop image for disease or pests and recommend treatment:\n\n"
                        f"data:{content_type};base64,{encoded_image}"
                    )
                    result = model.generate_content(prompt)
                    reply = result.text.replace("**", "*")

            except Exception as e:
                print(f"[IMAGE ERROR] {e}")
                reply = "Sorry, I couldn't process the image. Please send a valid crop photo."
        else:
            reply = "Only crop images are supported at the moment."
    else:
        # Handle normal text queries
        try:
            full_prompt = instructions + incoming_msg
            result = model.generate_content(full_prompt)
            reply = result.text.replace("**", "*")
        except Exception as e:
            print(f"[TEXT ERROR] {e}")
            reply = "Sorry, I'm having trouble answering that right now."

    # 📤 Send reply
    response = MessagingResponse()
    message = response.message()
    message.body(reply)
    return str(response)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
