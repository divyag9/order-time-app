import os
from flask import Flask
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient

app = Flask(__name__)
app.config["DEBUG"] = True

proxy_client = TwilioHttpClient()
proxy_client.session.proxies = {'https': os.environ['https_proxy']}

@app.route('/')
def hello_world():
	print("hi")
	account_sid = "AC4b299cccdd9f1ce0a6687f32f2cdc751"
	auth_token = "cb81dda39984fb309f47a76f09d9c304"
	client = Client(account_sid, auth_token, http_client=proxy_client)
	call = client.messages.create(
    	to="+18103995947",
    	from_="+15862571827",
    	body="Helloo1")
	print(call.sid)
	return "hi"

if __name__ == "__main__":
    app.run()
