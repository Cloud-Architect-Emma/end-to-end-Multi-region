from flask import Flask, jsonify
import requests

app = Flask(__name__)

PRODUCT_SERVICE_URL = "http://productservice:5001/products"

@app.route("/cart")
def cart():
    # simple example cart
    products = requests.get(PRODUCT_SERVICE_URL).json()
    cart_items = products[:2]  # first 2 products
    return jsonify({"cart": cart_items})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
