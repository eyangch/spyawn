from flask import Flask, request
import docker
import json
import time
import random
import os

client = docker.from_env()

config = json.load(open("config.json"))
if not os.path.isdir("data"):
    os.mkdir("data")

app = Flask(__name__)

port_range = (50000, 60000)

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

@app.route("/get/<int:uid>/<chal>")
def get(uid, chal):
    res = {"time": 0, "port": 0}
    try:
        res = json.load(open("data/" + str(uid) + "." + chal))
    except:
        pass
    return res

@app.route("/remove/<int:uid>/<chal>")
def remove(uid, chal):
    if chal not in config:
        return {"status": "error", "message": "invalid chal"}
    chal_dat = get(uid, chal)
    if chal_dat["time"] < round(time.time()):
        return {"status": "error", "message": "chal already deleted"}
    del_container(uid, chal)
    return {"status": "yay"}

@app.route("/create/<int:uid>/<chal>")
def create(uid, chal):
    if chal not in config:
        return {"status": "error", "message": "invalid chal"}
    chal_dat = get(uid, chal)
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
