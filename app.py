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
from rq import Queue
import redis
from rq.job import Job

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder='frontend/build', static_url_path='/')
CORS(app)

# Connect to MongoDB
uri = os.environ.get("MONGO_URI")
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["macysdata"]
collection = db["items"]

# Connect to Redis
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
logging.info(f"Connecting to Redis at: {redis_url}")
conn = redis.from_url(redis_url)
q = Queue(connection=conn)

def serialize_doc(doc):
    doc['_id'] = str(doc['_id'])
    return doc

def scrape_task(keyword):
    if keyword.isnumeric():
        results = asyncio.run(scrape_individual_item(keyword, None))
    else:
        results = asyncio.run(scrape_macys_data(keyword))
    return results

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

        job = q.enqueue(scrape_task, keyword)
        return jsonify({"message": "Scraping started", "job_id": job.get_id()}), 202
    except Exception as e:
        logging.error(f"Error in /scrape: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_job/<job_id>", methods=["GET"])
def get_job(job_id):
    try:
        job = Job.fetch(job_id, connection=conn)
        if job.is_finished:
            return jsonify({"status": "finished", "result": job.result}), 200
        else:
            return jsonify({"status": job.get_status()}), 200
    except Exception as e:
        logging.error(f"Error in /get_job: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
        data_set = {item['product_name'] for item in data}

        all_documents = list(collection.find({"device_id": device_id}))

        for listing in all_documents:
            if listing["product_name"] not in data_set:
                collection.delete_one({"_id": listing["_id"]})
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

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    http_server = WSGIServer(('0.0.0.0', port), app)
    http_server.serve_forever()
