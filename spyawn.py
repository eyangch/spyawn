from flask import Flask, request
import docker
import json
import time
import random

client = docker.from_env()

config = json.load(open("config.json"))

app = Flask(__name__)

port_range = (50000, 60000)

def make_container(uid, chal):
    container = None
    port = None
    while True:
        try:
            port = random.randint(port_range[0], port_range[1])
            container = client.containers.run(chal, ports={str(config[chal]["internal_port"]) + "/tcp": port}, **(config[chal]["container"]))
            break
        except Exception as e:
            print(e)
    with open("data/" + str(uid) + "." + chal, "w") as f:
        json.dump({"time": round(time.time() + config[chal]["container"]["healthcheck"]["interval"]//1000000000), "port": port}, f)

@app.route("/get/<int:uid>/<chal>")
def get(uid, chal):
    res = {"time": 0, "port": 0}
    try:
        res = json.load(open("data/" + str(uid) + "." + chal))
    except:
        pass
    return res

@app.route("/create/<int:uid>/<chal>")
def create(uid, chal):
    if chal not in config:
        return {"status": "error", "message": "invalid chal"}
    chal_dat = get(uid, chal)
    if chal_dat["time"] > round(time.time()):
        return {"status": "error", "message": "already active chal"}
    make_container(uid, chal)
    return {"status": "yay"}