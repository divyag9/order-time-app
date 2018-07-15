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
app.config['DEBUG'] = True
# MySQL configurations
app.config['MYSQL_DATABASE_USER'] =  os.environ['MYSQL_DATABASE_USER']
app.config['MYSQL_DATABASE_PASSWORD'] = os.environ['MYSQL_DATABASE_PASSWORD']
app.config['MYSQL_DATABASE_DB'] = os.environ['MYSQL_DATABASE_DB']
app.config['MYSQL_DATABASE_HOST'] = os.environ['MYSQL_DATABASE_HOST']
mysql.init_app(app)

# logging config
logging.basicConfig(level=logging.DEBUG)

# set twilio client
proxy_client = TwilioHttpClient()
proxy_client.session.proxies = {'https': os.environ['https_proxy']}

# send message using the twilio account
def send_message(cell_phone_number, message):
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    client = Client(account_sid, auth_token, http_client=proxy_client)
    call = client.messages.create(
    	to=cell_phone_number,
    	from_='+15862571827',
    	body=message)

# get order information from mysql database
def get_order_information(order_number):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ORDERS WHERE ORDER_NUMBER=%s',(order_number))
    return conn, cursor

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/sendsms', methods=['POST'])
def send_sms():
    order_number = request.form['ordernumber']
    cell_phone_number = request.form['cellphonenumber']

    try:
        conn, cursor = get_order_information(order_number)
        row_count = cursor.rowcount
        # insert the order information into database if there is no record for that ordernumber else redirect to home page with an error message
        if row_count > 0:
            return render_template('index.html', error='Message already sent for order number: %s' %(order_number))
        else:
            # when the message is not sent for that record the message_sent_time will be set to null
            message_sent_time = None
            random_number = randint(0, 100)
            # send message only if the random number is even
            if (random_number % 2) == 0:
                send_message(cell_phone_number, 'Thank you for ordering from Haldi!  Your order will be ready to be picked up in 15 minutes.')
                now = datetime.now()
                message_sent_time = now.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('INSERT INTO ORDERS (ORDER_NUMBER, CELL_PHONE_NUMBER, MESSAGE_SENT_TIME) VALUES (%s, %s, %s)', (order_number,cell_phone_number, message_sent_time))
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

    try:
        conn, cursor = get_order_information(order_number)
        row_count = cursor.rowcount
        row = cursor.fetchone()
        # update the order with pickuptime if the ordernumber already exists else redirect to home page with an error message
        if row_count == 0:
            return render_template('index.html', error="Ordernumber: %s  doesn't exist, message was not sent previously" %(order_number))
        # if the pickup time is already updated don't update again.
        elif row[4] is not None:
            return render_template('index.html', error="Already confirmed pickup for ordernumber: %s" %(order_number))
        else:
            now = datetime.now()
            pickup_time = now.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('UPDATE ORDERS SET PICKUP_TIME = %s WHERE ORDER_NUMBER= %s', (pickup_time,order_number))
            conn.commit()
        # once pickedup send survey question
        cell_phone_number = row[2]
        send_message(cell_phone_number, 'We hope you enjoyed your meal from Haldi! Please help us improve our service by rating your take-out order experience on a scale of 1-5, with 5 being the most positive.')
    except Exception as e:
        logging.error(e)
        return render_template('index.html', error=str(e))
    finally:
        cursor.close()
        conn.close()

    return render_template('index.html', message='Pickup confirmed')


