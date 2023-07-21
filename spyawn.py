from flask import Flask, request
import docker
import json
import time
import random
import os
import requests

client = docker.from_env()

config = json.load(open("config.json"))
if not os.path.isdir("data"):
    os.mkdir("data")
if not os.path.isdir("rates"):
    os.mkdir("rates")

app = Flask(__name__)

port_range = (50000, 60000)

@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

def make_container(uid, chal):
    container = None
    port = None
    while True:
        try:
            port = random.randint(port_range[0], port_range[1])
            container = client.containers.run(chal, ports={str(config[chal]["internal_port"]) + "/tcp": port}, name=chal+str(uid), **(config[chal]["container"]))
            break
        except Exception as e:
            print(e)
    print("CREATED: " + str(uid) + " " + chal)
    with open("data/" + str(uid) + "." + chal, "w") as f:
        json.dump({"time": round(time.time() + config[chal]["container"]["healthcheck"]["interval"]//1000000000), "port": port}, f)

def del_container(uid, chal):
    container = None
    print("KILLED: " + str(uid) + " " + chal)
    try:
        container = client.containers.get(chal + str(uid))
        container.kill()
    except Exception as e:
        print(e)
        return
    with open("data/" + str(uid) + "." + chal, "w") as f:
        json.dump({"time": 0, "port": 0}, f)

def verify_id(uid):
    r = requests.get("http://5.161.201.219:8000/api/checkTeamId/" + str(uid))
    return r.json()["teamIdExists"]

def ratelimit(ip):
    if not os.path.isfile("rates/" + ip):
        with open("rates/" + ip, "w") as f:
            f.write("0")
    with open("rates/" + ip) as f:
        prev_t = int(f.read())
        if prev_t == round(time.time()):
            return False
    with open("rates/" + ip, "w") as f:
        f.write(str(round(time.time())))
    return True

def aux_get(uid, chal):
    res = {"time": 0, "port": 0}
    try:
        res = json.load(open("data/" + str(uid) + "." + chal))
    except:
        pass
    return res


@app.route("/get/<int:uid>/<chal>")
def get(uid, chal):
    if not ratelimit(request.remote_addr):
        return {"status": "error", "message": "rate limit exceeded"}
    if not verify_id(uid):
        return {"status": "error", "message": "invalid team"}
    return aux_get(uid, chal)

@app.route("/remove/<int:uid>/<chal>")
def remove(uid, chal):
    if not ratelimit(request.remote_addr):
        return {"status": "error", "message": "rate limit exceeded"}
    if not verify_id(uid):
        return {"status": "error", "message": "invalid team"}
    if chal not in config:
        return {"status": "error", "message": "invalid chal"}
    chal_dat = aux_get(uid, chal)
    if chal_dat["time"] < round(time.time()):
        return {"status": "error", "message": "chal already deleted"}
    del_container(uid, chal)
    return {"status": "yay"}

@app.route("/create/<int:uid>/<chal>")
def create(uid, chal):
    if not ratelimit(request.remote_addr):
        return {"status": "error", "message": "rate limit exceeded"}
    if not verify_id(uid):
        return {"status": "error", "message": "invalid team"}
    if chal not in config:
        return {"status": "error", "message": "invalid chal"}
    chal_dat = aux_get(uid, chal)
    if chal_dat["time"] > round(time.time()):
        return {"status": "error", "message": "already active chal"}
    del_container(uid, chal)
    make_container(uid, chal)
    return {"status": "yay"}

@app.route("/reloadconfig")
def reloadconfig():
    global config
    config = json.load(open("config.json"))
    return "😳"
