from flask import Flask, render_template

app = Flask(__name__)

# 0.0.0.0:5000
@app.route("/")
def main():
    return render_template('main_ailen.html')

@app.route("/signup")
def signup():
    return render_template('signup.html')

@app.route("/signin")
def signin():
    return render_template('signin.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)