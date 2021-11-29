from flask import Flask, render_template, jsonify, redirect, request, url_for
from functools import wraps
import pymysql
import time
import picamera
import RPi.GPIO as GPIO
import Adafruit_DHT
import spidev
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

def login_required(f):
    @wraps(f)
    def deco_func(*args, **kwargs):
        if session.get("id") is None:
            return redirect(url_for("signin"))
        return f(*args, **kwargs)
    return deco_func

app = Flask(__name__)
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
            sql = "INSERT INTO users VALUES ('%s', '%s')" % (id, pw)
            cursor.execute(db)
            data = cursor.fetchall()
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
        cur.execute("set names utf8")
        cur.execute(sql, value)
        data = cur.fetchall()
        cur.close()
        db.close()

        for row in data:
            data = row[0]
        if data:
            session['login_user'] = id
            session.permanet = True
            return redirect(url_for('bss'))
        else:
            err = 'Invalid ID or PW.'
    return render_template('signin.html', err=err)

@app.route("/main", methods=['GET', 'POST'])
@login_required
def main():
    err = None
    id = session['login_user']
    if request.method == 'GET':
        db = mysql.connect()
        cur = db.cursor()
        sql = "SELECT title, id, ntime FROM content ORDER BY times desc"
        cur.execute(sql)
        data = cur.fetchall()
        data_list = []
        for obj in data:
            data_list = {
                'title':obj[0],
                'writer':obj[1],
                'ntime':obj[2]
            }
        cur.close()
        db.close()
        return render_template('main.html', data_list=data_list)


@app.route("/picUpload", methods=['GET', 'POST'])
@login_required
def picUpload():
    global hum, tem, ntime, light
    err = None
    camera = picamera.PiCamera()
    if camera and sensor and spi:
        try:
            spi.open(0, 0)
            spi.max_speed_hz = 100000
            button = 0
            camera.resolution = (640, 480)
            
            camera.start_preview()
            GPIO.output(LED_PIN, GPIO.LOW)
            while not button:
                if(GPIO.input(SWITCH_PIN)):
                    GPIO.output(LED_PIN, GPIO.LOW)
                    button = 1
                    ntime = time.strftime("%Y%m%d_%H%M%S")
                    light = analog_read(0) / 1023 * 100
                    hum, tem = Adafruit_DHT.read_retry(sensor, DHT_PIN)
                    camera.capture('%s%s.jpg' % (path, ntime))

            camera.stop_preview()
            filename = path + ntime + '.jpg'
            return render_template('upload.html', filename=filename, hum=hum, tem=tem, ntime=ntime)
        finally:
            camera.close()
    else:
        err = "No Camera or LDR or DHT Ready."
    return render_template('upload.html', err=err)
@app.route("/upload.html", methods=['GET', 'POST'])
@login_required
def upload():
    err = None
    id = session['login_user']
    if request.form == POST:
        title = request.form['title']
        contents = request.form['contents']
        db = mysql.connect()
        cur = db.cursor()

        sql = "INSERT into content values(%s, %s, %s, %s, %s, %s, %s)"
        cur.execute(sql, (title, contents, id, filename, hum, tem, light))
        db.commit()
        db.close()
        data = cur.fetchall()

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", debug=True)
    finally:
        GPIO.cleanup()

