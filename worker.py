import redis
from rq import Worker, Queue, Connection
import os
from dotenv import load_dotenv

load_dotenv()

listen = ['default']


conn = redis.from_url("redis://localhost:6379/0")

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
