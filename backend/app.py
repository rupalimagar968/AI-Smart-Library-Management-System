from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "service": "backend",
        "status": "UP"
    })


@app.route("/health")
def health():
    return jsonify({
        "service": "backend",
        "status": "UP"
    })


@app.route("/api/health")
def api_health():
    return jsonify({
        "service": "backend",
        "status": "UP"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
