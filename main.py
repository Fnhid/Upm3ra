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
#=======연결한 GPIO에 맞게 설정해주세요.========
LED_PIN = 17   # LED                    
SWITCH_PIN = 6 # 스위치
DHT_PIN = 18   # 온습도
#===========================================

GPIO.setmode(GPIO.BCM)              
GPIO.setup(LED_PIN, GPIO.OUT)       
GPIO.setup(SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
global hum, tem, ntime, light, filename 
path = './static/images/' # 이미지 저장 기본 경로 설정

spi = spidev.SpiDev()  

def analog_read(channel):
    ret = spi.xfer2([1, (channel + 8) << 4, 0])
    adc_out = ((ret[1] & 3) << 8) + ret[2]
    return adc_out # 아날로그값 처리해주는 함수


app = Flask(__name__) # 앱 시작
app.secret_key = os.urandom(24) 
mysql = MySQL() 
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'toor'
app.config['MYSQL_DATABASE_DB'] = 'upm3ra'
app.config['MYSQL_DATABASE_HOST'] = 'localhost' # DB 정보 입력
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
        ckpw = request.form['ckpw'] # 비밀번호 확인

        db = mysql.connect()
        cur = db.cursor()
        if pw == ckpw: # 비밀번호 확인 성공시
            sql = "INSERT INTO users VALUES (%s, %s)" 
            value = (id, pw) 
            cur.execute(sql, value) # users 테이블에 id, pw로 추가
            data = cur.fetchall() # 반환값 받아오기
            if not data: # 성공시
                db.commit() 
                return redirect(url_for('ailen'))
            else: # 실패시
                db.rollback() # DB 복원 후 error 설정
                err = "Register Failed"
        else: # 비밀번호 확인 실패시
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
        cur.execute(sql, value) # id와 pw를 db에서 찾음
        data = cur.fetchall()
        cur.close()
        db.close()

        for row in data:
            data = row[0]
        if data: # 성공시
            session['login_user'] = id # 세션 부여
            session.permanet = True
            return redirect(url_for('main')) # main 리다이렉트
        else: 
            err = 'Invalid ID or PW.'
    return render_template('signin.html', err=err)

@app.route("/main", methods=['GET', 'POST'])
def main():
    if session: # 세션 필요
        err = None
        if request.method == 'GET': 
            user=session['login_user']
            db = mysql.connect()
            cur = db.cursor()
            sql = "SELECT title, id, contents, filename, hum, tem, light FROM content ORDER BY filename desc"
            cur.execute(sql) # content 테이블에서 게시물 정보를 튜플로 받아옴
            data = cur.fetchall()
            cur.close()
            db.close()
            return render_template('main.html', data_list=data, user=user)
    else:
        return redirect(url_for('signin'))


@app.route("/picUpload", methods=['GET', 'POST'])
def picUpload():
    global hum, tem, ntime, light, filename
    if session: # 세션 필요
        loadsucc = 0
        err = None
        camera = picamera.PiCamera()
        camera.resolution = (640, 480)
        camera.start_preview()
        try:
            if camera and sensor and spi: # 카메라, 온습도 모듈, 조도센서가 연결되어있는지 확인
                loadsucc = 1 # 카메라, 온습도 모듈, 조도센서가 연결되었는지 체크해주는 FLAG
                spi.open(0, 0)
                spi.max_speed_hz = 100000
                GPIO.output(LED_PIN, GPIO.HIGH)
                GPIO.wait_for_edge(SWITCH_PIN, GPIO.RISING) # 스위치가 눌리기까지 대기
                GPIO.output(LED_PIN, GPIO.LOW)
                ntime = time.strftime("%Y%m%d_%H%M%S")
                light = str(int(analog_read(0) / 1023 * 100)) + "%"
                hum, tem = Adafruit_DHT.read_retry(sensor, DHT_PIN)
                hum = str(int(hum)) + "%"
                tem = str(int(tem)) + "℃" # 정보 측정
                camera.capture('%s%s.jpg' % (path, ntime)) # 카메라 촬영 및 저장
                filename = path + ntime + '.jpg'
                
                return redirect(url_for('upload')) # 추가 정보 입력을 위해 upload로 리다이렉트
            else:
                err = "No Camera or LDR or DHT Ready."
                
                GPIO.output(LED_PIN, GPIO.LOW)
        finally:
            camera.stop_preview()
            camera.close()
            if not loadsucc: # 카메라, 온습도 모듈, 조도센서가 연결되지 않았을 때
                return render_template('picUpload.html', err=err)
    else:
        return render_template('main.html', data_list=data, user=user)
    
@app.route("/upload", methods=['GET', 'POST'])
def upload():
    global hum, tem, light, filename
    err = None
    if session: # 로그인 필요
        user = session['login_user']
        if request.method == 'POST':
            title = request.form['title']
            contents = request.form['contents'] # 제목과 내용을 입력받음
            db = mysql.connect()
            cur = db.cursor()
            sql = "INSERT INTO content VALUES (%s, %s, %s, %s, %s, %s, %s)"
            value = (title, contents, user, filename, hum, tem, light) # content 테이블에 저장
            cur.execute(sql, value)
            data = cur.fetchall()
            if not data:
                db.commit()
                return redirect(url_for('main')) # 성공시 커밋하고 main으로 리다이렉트
            else:
                db.rollback()
                err = "Uploading failed.." # 실패시 DB 복원 후 error 설정
        return render_template("upload.html", err=err, hum=hum, tem=tem, light=light, filename=filename)
    else:
        return render_template("main.html")
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", debug=True)
    finally:
        GPIO.cleanup()

