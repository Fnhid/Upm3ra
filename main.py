from flask import Flask, render_template, jsonify, redirect, request, url_for, session
from functools import wraps
import pymysql
import time
import picamera
import RPi.GPIO as GPIO
import Adafruit_DHT
import spidev
import os
import numpy as np
from flask_session import Session
from flaskext.mysql import MySQL
GPIO.setwarnings(False)
sensor = Adafruit_DHT.DHT11
#=====================
LED_PIN = 17
SWITCH_PIN = 6
DHT_PIN = 18
#=====================
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

path = '/home/pi/Upm3ra/static/images/pic/'

spi = spidev.SpiDev()



def analog_read(channel):
    ret = spi.xfer2([1, (channel + 8) << 4, 0])
    adc_out = ((ret[1] & 3) << 8) + ret[2]
    return adc_out


app = Flask(__name__)
app.secret_key = os.urandom(24)
mysql = MySQL()
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'toor'
app.config['MYSQL_DATABASE_DB'] = 'upm3ra'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)
@app.route("/")
def ailen():
    return render_template('ailen.html')

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    err = None
    if request.method == 'POST':
        id = request.form['id']
        pw = request.form['pw']
        ckpw = request.form['ckpw']

        db = mysql.connect()
        cur = db.cursor()
        if pw == ckpw:
            sql = "INSERT INTO users VALUES (%s, %s)" 
            value = (id, pw)
            cur.execute(sql, value)
            data = cur.fetchall()
            if not data:
                db.commit()
                return redirect(url_for('ailen'))
            else:
                db.rollback()
                err = "Register Failed"
        else:
            err = "Password Check Failed."
    return render_template('signup.html', err=err)

@app.route("/signin", methods=['GET', 'POST'])
def signin():
    err = None
    if request.method == 'POST':
        id = request.form['id']
        pw = request.form['pw']
        db = mysql.connect()
        cur = db.cursor()
        sql = "SELECT id FROM users WHERE id = %s AND pw = %s"
        value = (id, pw)
        cur.execute(sql, value)
        data = cur.fetchall()
        cur.close()
        db.close()

        for row in data:
            data = row[0]
        if data:
            session['login_user'] = id
            session.permanet = True
            return redirect(url_for('main'))
        else:
            err = 'Invalid ID or PW.'
    return render_template('signin.html', err=err)

@app.route("/main", methods=['GET', 'POST'])
def main():
    if session:
        err = None
        if request.method == 'GET':
            user=session['login_user']
            db = mysql.connect()
            cur = db.cursor()
            sql = "SELECT title, id, contents, filename, hum, tem, light FROM content ORDER BY filename desc"
            cur.execute(sql)
            data = cur.fetchall()
            cur.close()
            db.close()
            return render_template('main.html', data_list=data, user=user)
    else:
        return render_template('signin.html')


@app.route("/picUpload", methods=['GET', 'POST'])
def picUpload():
    global hum, tem, ntime, light, filename #vuln..
    if session:
        loadsucc = 0
        err = None
        camera = picamera.PiCamera()
        camera.resolution = (640, 480)
        camera.start_preview()
        try:
            if camera and sensor and spi:
                spi.open(0, 0)
                spi.max_speed_hz = 100000
                GPIO.output(LED_PIN, GPIO.HIGH)
                GPIO.wait_for_edge(6, GPIO.RISING)
                GPIO.output(LED_PIN, GPIO.LOW)
                ntime = time.strftime("%Y%m%d_%H%M%S")
                light = analog_read(0) / 1023 * 100
                hum, tem = Adafruit_DHT.read_retry(sensor, DHT_PIN)
                camera.capture('%s%s.jpg' % (path, ntime))
                filename = path + ntime + '.jpg'
                loadsucc = 1
                return redirect(url_for('upload'))
            else:
                err = "No Camera or LDR or DHT Ready."
                
                GPIO.output(LED_PIN, GPIO.LOW)
        finally:
            camera.stop_preview()
            camera.close()
            if not loadsucc:
                return render_template('picUpload.html', err=err)
    else:
        return render_template('main.html', data_list=data, user=user)
    
@app.route("/upload", methods=['GET', 'POST'])
def upload():
    err = None
    if session:

        if request.form == 'POST':
            title = request.form['title']
            contents = request.form['contents']
            light = request.form['light']
            filename = request.form['filename']
            db = mysql.connect()
            cur = db.cursor()
            sql = "INSERT into content values (%s, %s, %s, %s, %s, %s, %s)"
            cur.execute(sql, (title, contents, id, filename, hum, tem, light))
            db.commit()
            db.close()
            data = cur.fetchall()
            if data:
                return redirect(url_for('main'))
            else:
                err = 'Failed..'
        return render_template("upload.html", err=err, hum=hum, tem=tem, light=light, filename=filename)
    else:
        return render_template("main.html")
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", debug=True)
    finally:
        GPIO.cleanup()

