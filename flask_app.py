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

# get all orders whose pickup time is null
def get_orders(conn, cursor):
    cursor.execute('SELECT * FROM ORDERS WHERE PICKUP_TIME IS NULL')

    return cursor.fetchall()

@app.route('/')
def main():
    orders = None

    # display orders that are not completed yet(that is pick up is not confirmed)
    try:
        conn = mysql.connect()
        cursor = conn.cursor()
        orders = get_orders(conn, cursor)

        return render_template('index.html', orders=orders)
    except Exception as e:
        logging.error(e)

        return render_template('index.html', error=str(e), orders=orders)
    finally:
        cursor.close()
        conn.close()

@app.route('/createorder', methods=['POST'])
def create_order():
    order_number = request.form['ordernumber']
    cell_phone_number = request.form['cellphonenumber']
    orders = None

    try:

        conn, cursor = get_order_information(order_number)
        row_count = cursor.rowcount
        #send back incomplete orders on each render
        orders = get_orders(conn, cursor)
        # insert the order information into database if there is no record for that ordernumber else redirect to home page with an error message
        if row_count > 0:
            return render_template('index.html', error='Order number: %s already exists' %(order_number), orders=orders)
        else:
            cursor.execute('INSERT INTO ORDERS (ORDER_NUMBER, CELL_PHONE_NUMBER) VALUES (%s, %s)', (order_number,cell_phone_number))
            conn.commit()
        #send back incomplete orders
        orders = get_orders(conn, cursor)

        return render_template('index.html', message='Order Created', orders=orders)
    except Exception as e:
        logging.error(e)
        #send back incomplete orders
        orders = get_orders(conn, cursor)

        return render_template('index.html', error=str(e), orders=orders)
    finally:
        cursor.close()
        conn.close()

@app.route('/sendsms', methods=['POST'])
def send_sms():
    order_number = request.form['sms_ordernumber']
    orders = None

    try:
        conn, cursor = get_order_information(order_number)
        row = cursor.fetchone()
        # phone number to send message to
        cell_phone_number = row[2]
        # when the message is not sent for that record the message_sent_time will be set to null
        message_sent_time = None
        random_number = randint(0, 100)
        # send message only if the random number is even
        if (random_number % 2) == 0:
            send_message(cell_phone_number, 'Thank you for ordering from Haldi! Your order will be ready to be picked up in 15 minutes.')
            now = datetime.now()
            message_sent_time = now.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('UPDATE ORDERS SET MESSAGE_SENT_TIME = %s WHERE ORDER_NUMBER= %s', (message_sent_time,order_number))
        conn.commit()
        #send back incomplete orders
        orders = get_orders(conn, cursor)

        return render_template('index.html', message='Message Sent', orders=orders, sendsms_ordernumber=order_number)
    except Exception as e:
        logging.error(e)
        #send back incomplete orders
        orders = get_orders(conn, cursor)

        return render_template('index.html', error=str(e), orders=orders)
    finally:
        cursor.close()
        conn.close()

@app.route('/confirmpickup', methods=['POST'])
def confirm_pickup():
    order_number = request.form['pickup_ordernumber']
    orders = None

    try:
        conn, cursor = get_order_information(order_number)
        row = cursor.fetchone()

        # once pickedup send survey question
        cell_phone_number = row[2]
        send_message(cell_phone_number, 'We hope you enjoyed your meal from Haldi! Please help us improve our service by rating your take-out order experience on a scale of 1-5, with 5 being the most positive.')

        now = datetime.now()
        pickup_time = now.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('UPDATE ORDERS SET PICKUP_TIME = %s WHERE ORDER_NUMBER= %s', (pickup_time,order_number))
        conn.commit()
        #send back incomplete orders
        orders = get_orders(conn, cursor)

        return render_template('index.html', message='Pickup confirmed', orders=orders)
    except Exception as e:
        logging.error(e)
        #send back incomplete orders
        orders = get_orders(conn, cursor)

        return render_template('index.html', error=str(e), orders=orders)
    finally:
        cursor.close()
        conn.close()


