from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from gather import scrape_macys_data
from individual import scrape_individual_item
import asyncio
import pymongo
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import os
import logging
from gevent.pywsgi import WSGIServer
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder='frontend/build', static_url_path='/')
CORS(app)

# Connect to MongoDB
#uri = os.environ.get("MONGO_URI")
client = MongoClient("mongodb+srv://micleung168:yY4IqraFsBQ0HHmL@macys.5qpvkbi.mongodb.net/?retryWrites=true&w=majority&appName=macys", server_api=ServerApi('1'))
db = client["macysdata"]
collection = db["items"]

executor = ThreadPoolExecutor(max_workers=5)

def serialize_doc(doc):
    doc['_id'] = str(doc['_id'])
    return doc

@app.route("/scrape", methods=["POST"])
def scrape():
    try:
        logging.info("Scrape endpoint called")
        data = request.get_json()
        keyword = data.get('keyword', '')
        logging.info(f"Keyword: {keyword}")
        if not keyword:
            return jsonify({"error": "No keyword provided"}), 400
        keyword = keyword.replace(' ', '-')

        future = executor.submit(scrape_task, keyword)
        results = future.result()
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error in /scrape: {str(e)}")
        return jsonify({"error": str(e)}), 500

def scrape_task(keyword):
    if keyword.isnumeric():
        results = asyncio.run(scrape_individual_item(keyword, None))
    else:
        results = asyncio.run(scrape_macys_data(keyword))
    return results

@app.route("/gather", methods=["POST"])
def gather():
    try:
        data = request.get_json()
        device_id = request.args.get('device_id')
        if not device_id:
            return jsonify({"message": "Device ID is required"}), 400
        for item in data:
            item["device_id"] = device_id
            existing_item = collection.find_one({"product_name": item["product_name"], "device_id": device_id})
            if not existing_item:
                item["prices"] = [{"price": item["sale_price"], "date": datetime.utcnow()}]
                collection.insert_one(item)
        #data_set = {item['product_name'] for item in data}
        #all_documents = list(collection.find())
        #for listing in all_documents:
         #   if listing["product_name"] not in data_set:
          #      collection.delete_one({"_id": listing["_id"]})
        return jsonify({"message": "Database updated successfully"}), 200
    except Exception as e:
        logging.error(f"Error in /gather: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_data", methods=["GET"])
def get_data():
    try:
        device_id = request.args.get('device_id')
        if not device_id:
            return jsonify({"message": "Device ID is required"}), 400
        data = list(collection.find({"device_id": device_id}))
        serialized_data = [serialize_doc(doc) for doc in data]
        return jsonify(serialized_data)
    except Exception as e:
        logging.error(f"Error in /get_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists("frontend/build/" + path):
        return send_from_directory('frontend/build', path)
    else:
        return send_from_directory('frontend/build', 'index.html')

def update_price():
    print("Running scheduled update_price")
    data = list(collection.find())
    count = 0
    for item in data:
        try:
            print(f"Checking {count + 1} item / {len(data)}")
            results = asyncio.run(scrape_individual_item(None, item["product_link"]))
            if results and len(results) > 0:
                sale_price = results[0].get("sale_price", "N/A")
                original_price = results[0].get("original_price", "N/A")
                new_price_entry = {
                    "price": sale_price if sale_price != "N/A" else original_price,
                    "date": datetime.utcnow()
                }
                collection.update_one(
                    {"_id": item["_id"]},
                    {"$push": {"prices": new_price_entry}}
                )
                count += 1
            else:
                print(f"No valid results for item {item['_id']}")
        except Exception as e:
            print(f"Failed to update item {item['_id']}: {e}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    http_server = WSGIServer(('0.0.0.0', port), app)
    http_server.serve_forever()
