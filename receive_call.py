from fastapi import FastAPI, Request, Response
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client

from dotenv import load_dotenv


load_dotenv()

app = FastAPI()
twilio_client = Client()


@app.get("/call")
def call(request: Request):
    """Accept a phone call."""

    # intiazlize voice response
    response = VoiceResponse()
    response.say("Hello world")

    return Response(content=str(response), media_type="application/xml")


@app.get("/call")
def call(request: Request):
    """Accept a phone call."""

    # intiazlize voice response
    response = VoiceResponse()
    response.say("Hello world")

    return Response(content=str(response), media_type="application/xml")


if __name__ == "__main__":
    from pyngrok import ngrok
    import uvicorn

    port = 5000
    
    public_url = ngrok.connect(port, bind_tls=True).public_url
    # print("Numbers: ", twilio_client.incoming_phone_numbers.list())

    number = twilio_client.incoming_phone_numbers.list()[0]
    number.update(voice_url=public_url + "/call")
    print(f"Waiting for calls on {number.phone_number} public url: {public_url}")

    uvicorn.run("receive_call:app", host="localhost", port=port, log_level="critical")
