from flask import Flask, render_template

app = Flask(__name__)

# 0.0.0.0:5000
@app.route("/")
def main():
    return render_template('main.html')



if __name__ == "__main__":
    app.run(host="0.0.0.0")