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
from rq import Queue
from worker import conn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder='frontend/build', static_url_path='/')
CORS(app)

# Connect to MongoDB
uri = os.getenv("MONGO_URI")
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["macysdata"]
collection = db["items"]

q = Queue(connection=conn)

def serialize_doc(doc):
    doc['_id'] = str(doc['_id'])
    return doc

def scrape_task(keyword):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if keyword.isnumeric():
        results = loop.run_until_complete(scrape_individual_item(keyword, None))
    else:
        results = loop.run_until_complete(scrape_macys_data(keyword))
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
        return jsonify({"job_id": job.get_id()}), 202
    except Exception as e:
        logging.error(f"Error in /scrape: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/job_status/<job_id>", methods=["GET"])
def job_status(job_id):
    from rq.job import Job
    job = Job.fetch(job_id, connection=conn)
    if job.is_finished:
        return jsonify(job.result), 200
    elif job.is_failed:
        return jsonify({"status": "failed"}), 500
    else:
        return jsonify({"status": job.get_status()}), 202

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
    app.run(host='0.0.0.0', port=port)
