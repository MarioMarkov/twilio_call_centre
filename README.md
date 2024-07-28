# Twilio AI Call Center

## Overview

This project is a FastAPI-based service designed to handle voice interactions through Twilio with an AI bot.

### Prerequisites

- Python 3.10+
- Twilio Account with a phone number
- Azure Speech Services Subscription
- Ngrok for local development and testing

### Installation

1. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   Create a `.env` file in the project root and add the necessary environment variables:
   ```env
   TWILIO_ACCOUNT_SID=<your_twilio_account_sid>
   TWILIO_AUTH_TOKEN=<your_twilio_auth_token>
   OPENAI_API_KEY=<your_openai_api_key>
   SPEECH_KEY=<your_azure_speech_key>
   SPEECH_REGION=<your_azure_speech_region>
   NGROK_AUTHTOKEN=<your_ngrok_auth_token>
   ```

## Running the Service

1. Start the FastAPI application and starting the ngrok tunnel:

   ```bash
   python main.py
   ```

2. Update the ngrok domain from the ngrok website:
   ```python
   listener = ngrok.forward(f"http://localhost:{port}", authtoken_from_env=True, domain="your_ngrok_domain.ngrok-free.app")
   ```

## Example Usage

1. Make a call to your Twilio phone number.
2. The call details are processed, and an audio stream is initiated.
3. Speech recognition processes the audio stream in real-time.
4. Recognized speech is sent to the bot agent, which generates a response.
5. The response is sent back through the WebSocket and played to the caller.

## License

This project is licensed under the Apache License 2.0.

## Contact

For any inquiries or issues, please contact [mario11septemvri@gmail.com].
