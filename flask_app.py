import os
import logging
from flask import Flask, render_template, request
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
from flaskext.mysql import MySQL
from datetime import datetime
from random import randint

mysql = MySQL()
app = Flask(__name__)
app.config["DEBUG"] = True
# MySQL configurations
app.config['MYSQL_DATABASE_USER'] =  os.environ['MYSQL_DATABASE_USER']
app.config['MYSQL_DATABASE_PASSWORD'] = os.environ['MYSQL_DATABASE_PASSWORD']
app.config['MYSQL_DATABASE_DB'] = os.environ['MYSQL_DATABASE_DB']
app.config['MYSQL_DATABASE_HOST'] = os.environ['MYSQL_DATABASE_HOST']
mysql.init_app(app)

logging.basicConfig(level=logging.DEBUG)

proxy_client = TwilioHttpClient()
proxy_client.session.proxies = {'https': os.environ['https_proxy']}

def send_message(cell_phone_number, message):
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    client = Client(account_sid, auth_token, http_client=proxy_client)
    call = client.messages.create(
    	to=cell_phone_number,
    	from_="+15862571827",
    	body=message)

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/sendsms', methods=['POST'])
def send_sms():
    order_number = request.form['ordernumber']
    cell_phone_number = request.form['cellphonenumber']

    try:
        # send message only if the random number is even
        random_number = randint(0, 100)
        if (random_number % 2) == 0:
            send_message(cell_phone_number, "Your order will be ready to be picked up in 15 minutes")

        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * from ORDERS where ORDER_NUMBER=%s",(order_number))
        row_count = cursor.rowcount
        print("row_count: ", row_count)
        if row_count > 0:
            return render_template('index.html', error='Message already sent for order number: %s' %(order_number))
        else:
            now = datetime.now()
            message_sent_time = now.strftime('%Y-%m-%d %H:%M:%S')
            print("cell phone number: ", cell_phone_number)
            cursor.execute("INSERT INTO ORDERS (ORDER_NUMBER, CELL_PHONE_NUMBER, MESSAGE_SENT_TIME) VALUES (%s, %s, %s)", (order_number,cell_phone_number, message_sent_time))
            conn.commit()
    except Exception as e:
        logging.error(e)
        return render_template('index.html', error=str(e))
    finally:
        cursor.close()
        conn.close()

    return render_template('index.html', message='Message Sent')

@app.route('/confirmpickup', methods=['POST'])
def confirm_pickup():
    order_number = request.form['ordernumber']
    cell_phone_number = request.form['cellphonenumber']

    try:
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ORDERS WHERE ORDER_NUMBER=%s",(order_number))
        row_count = cursor.rowcount
        if row_count == 0:
            return render_template('index.html', error="Order number: %s  doesn't exist, message was not sent previously" %(order_number))
        else:
            now = datetime.now()
            pickup_time = now.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("UPDATE ORDERS SET PICKUP_TIME = %s WHERE ORDER_NUMBER= %s", (pickup_time,order_number))
            conn.commit()
        # once pickedup send survey question
        send_message(cell_phone_number, "How satisfied are you with the promptness of your order?\n0-worst, 10-exceptional")
    except Exception as e:
        logging.error(e)
        return render_template('index.html', error=str(e))
    finally:
        cursor.close()
        conn.close()

    return render_template('index.html', message='Updated pick up')


