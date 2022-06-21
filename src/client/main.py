from string import whitespace
import sys
import websockets
import requests
import asyncio
import threading
import json

username = input("Enter username: ")

SERVER = "localhost:8000"


async def send_message(url):
    async with websockets.connect(url) as websocket:
        while True:
            mesg_content = input(f"> {username}: ")
            message = {"sender": username, "message": mesg_content}
            await websocket.send(json.dumps(message))


async def receive_message(url):
    async with websockets.connect(url) as websocket:
        mesg_strlen = 0
        while True:
            message = await websocket.recv()
            msg_obj = json.loads(message)
            if msg_obj["sender"] == username:
                continue
            mesg_str = f"{msg_obj['sender']}: {msg_obj['message']}"
            whitespaces = " " * (mesg_strlen)
            print(f"\r{whitespaces}", end="\r")
            print(f"{msg_obj['sender']}: {msg_obj['message']}")
            print(f"> {username}: ", end="")
            sys.stdout.flush()
            mesg_strlen = len(mesg_str)


async def session_info(url):
    async with websockets.connect(url) as websocket:
        await websocket.send(json.dumps({"username": username}))
        session_info = await websocket.recv()
        print(session_info)

        while True:
            data = await websocket.recv()
            print(data)


def main():
    topics_list = requests.get("http://{SERVER}/messages/topics").json()
    print("Available topics:")
    for topic in topics_list:
        print(f"\t{topic}")
    topic = input("Enter topic: ")

    if topic not in topics_list:
        requests.post(f"http://{SERVER}/messages/create_topic", json={"topic": topic})

    ws_incoming_url = f"ws://{SERVER}/messages/incoming/{topic}"
    ws_outgoing_url = f"ws://{SERVER}/messages/outgoing/{topic}"
    ws_broadcast_url = f"ws://{SERVER}/messages/broadcast/{topic}"

    receiving_thread = threading.Thread(
        target=asyncio.run, args=(receive_message(ws_incoming_url),)
    )
    receiving_thread.daemon = True
    receiving_thread.start()

    broadcast_thread = threading.Thread(
        target=asyncio.run, args=(session_info(ws_broadcast_url),)
    )
    broadcast_thread.daemon = True
    broadcast_thread.start()

    sending_thread = threading.Thread(
        target=asyncio.run, args=(send_message(ws_outgoing_url),)
    )
    sending_thread.start()
    sending_thread.join()


if __name__ == "__main__":
    main()
