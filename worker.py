import redis
from rq import Worker, Queue, Connection
import os
from dotenv import load_dotenv

load_dotenv()

listen = ['default']

redis_url = os.getenv('REDIS_URL')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
