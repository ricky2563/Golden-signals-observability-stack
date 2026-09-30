import requests
import random
import time

BASE_URL = "http://localhost:5000"
ENDPOINTS = ["/api/fast", "/api/slow", "/api/unstable"]

# Pesos: fast e unstable mais frequentes, slow mais raro
WEIGHTS = [0.5, 0.2, 0.3]

print("Gerador de trafego a correr. Ctrl+C para parar.")

while True:
    endpoint = random.choices(ENDPOINTS, weights=WEIGHTS)[0]
    try:
        response = requests.get(BASE_URL + endpoint, timeout=5)
        print(f"{endpoint} -> {response.status_code}")
    except Exception as e:
        print(f"{endpoint} -> erro: {e}")

    time.sleep(random.uniform(0.01, 0.1))