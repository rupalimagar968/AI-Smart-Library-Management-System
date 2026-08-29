from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)

CORS(app)


@app.route("/")
def home():
    return jsonify({
        "message": "AI Smart Library Backend is running"
    })


@app.route("/api/health")
def health():
    return jsonify({
        "status": "UP",
        "service": "backend"
    })


@app.route("/api/books")
def books():
    books = [
        {
            "id": 1,
            "name": "Python Programming",
            "author": "Guido van Rossum"
        },
        {
            "id": 2,
            "name": "Artificial Intelligence",
            "author": "Stuart Russell"
        }
    ]

    return jsonify(books)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )