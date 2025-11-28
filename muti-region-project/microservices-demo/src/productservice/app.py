from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/products")
def products():
    sample_products = [
        {"id": 1, "name": "Laptop"},
        {"id": 2, "name": "Mouse"},
        {"id": 3, "name": "Keyboard"}
    ]
    return jsonify(sample_products)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
