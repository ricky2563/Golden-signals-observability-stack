from flask import Flask, jsonify, Response
import random
import time
import psutil
import os
import json
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# ---------- Logging estruturado (JSON, uma linha por evento) ----------
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key in ("endpoint", "status", "duration_ms"):
            if hasattr(record, key):
                log[key] = getattr(record, key)
        return json.dumps(log)

handler = logging.FileHandler(os.path.join(LOG_DIR, "api.log"), encoding="utf-8")
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# ---------- Metricas de saturacao ----------
process = psutil.Process(os.getpid())
process.cpu_percent(interval=None)  # "aquece" a medicao, a primeira chamada devolve sempre 0
cpu_usage = Gauge('app_process_cpu_percent', 'Uso de CPU do processo (%)')
memory_usage = Gauge('app_process_memory_bytes', 'Memoria RSS usada pelo processo (bytes)')

# ---------- Metricas de negocio ----------
REQUEST_COUNT = Counter(
    'app_requests_total',
    'Total de pedidos recebidos',
    ['endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'app_request_duration_seconds',
    'Duracao dos pedidos em segundos',
    ['endpoint']
)

@app.route('/api/fast')
def fast_endpoint():
    start = time.time()
    time.sleep(random.uniform(0.01, 0.1))
    duration = time.time() - start
    REQUEST_LATENCY.labels(endpoint='fast').observe(duration)
    REQUEST_COUNT.labels(endpoint='fast', status='success').inc()
    logger.info("request completed", extra={"endpoint": "fast", "status": 200, "duration_ms": round(duration * 1000, 1)})
    return jsonify({"status": "ok", "endpoint": "fast"})

@app.route('/api/slow')
def slow_endpoint():
    start = time.time()
    time.sleep(random.uniform(0.3, 0.8))
    duration = time.time() - start
    REQUEST_LATENCY.labels(endpoint='slow').observe(duration)
    REQUEST_COUNT.labels(endpoint='slow', status='success').inc()
    logger.info("request completed", extra={"endpoint": "slow", "status": 200, "duration_ms": round(duration * 1000, 1)})
    return jsonify({"status": "ok", "endpoint": "slow"})

@app.route('/api/unstable')
def unstable_endpoint():
    start = time.time()
    time.sleep(random.uniform(0.05, 0.2))
    duration = time.time() - start
    REQUEST_LATENCY.labels(endpoint='unstable').observe(duration)

    if random.random() < 0.2:
        REQUEST_COUNT.labels(endpoint='unstable', status='error').inc()
        logger.error("request failed: something went wrong", extra={"endpoint": "unstable", "status": 500, "duration_ms": round(duration * 1000, 1)})
        return jsonify({"status": "error", "message": "Something went wrong"}), 500

    REQUEST_COUNT.labels(endpoint='unstable', status='success').inc()
    logger.info("request completed", extra={"endpoint": "unstable", "status": 200, "duration_ms": round(duration * 1000, 1)})
    return jsonify({"status": "ok", "endpoint": "unstable"})

@app.route('/metrics')
def metrics():
    cpu_usage.set(process.cpu_percent(interval=None))
    memory_usage.set(process.memory_info().rss)
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(port=5000)