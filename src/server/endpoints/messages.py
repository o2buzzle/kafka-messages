from imp import C_EXTENSION
from math import prod
from typing import List
import fastapi
import aiokafka, kafka
import json
import configparser


config = configparser.ConfigParser()
config.read("config.ini")

kafka_bootstrap_server = "localhost:9092"

router = fastapi.APIRouter()

admin_client = kafka.KafkaAdminClient(bootstrap_servers=[kafka_bootstrap_server])


@router.websocket("/incoming/{topic}")
async def query_incomming_messages(websocket: fastapi.WebSocket, topic: str):
    if topic not in admin_client.list_topics():
        websocket.close(code=404)
        return
    await websocket.accept()
    consumer = aiokafka.AIOKafkaConsumer(
        topic,
        bootstrap_servers=[kafka_bootstrap_server],
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )
    await consumer.start()

    while True:
        try:
            msg = await consumer.getone()
            # print(msg)
            if msg is not None:
                await websocket.send_json(msg.value)
        except Exception:
            await consumer.stop()
            break


@router.websocket("/outgoing/{topic}")
async def send_message(websocket: fastapi.WebSocket, topic: str):
    if topic not in admin_client.list_topics():
        websocket.close(code=404)
        return
    await websocket.accept()

    producer = aiokafka.AIOKafkaProducer(
        bootstrap_servers=[kafka_bootstrap_server],
        value_serializer=lambda x: json.dumps(x).encode("utf-8"),
    )
    await producer.start()

    while True:
        try:
            message = await websocket.receive_json()
            # print(message)
            await producer.send(topic, message)
            await websocket.send_json({"status": "ok"})
        except fastapi.WebSocketDisconnect:
            await producer.stop()
            break


@router.websocket("/broadcast/{topic}")
async def broadcast_message(websocket: fastapi.WebSocket, topic: str):
    if topic not in admin_client.list_topics():
        websocket.close(code=404)
        return
    await websocket.accept()

    producer = aiokafka.AIOKafkaProducer(
        bootstrap_servers=[kafka_bootstrap_server],
        value_serializer=lambda x: json.dumps(x).encode("utf-8"),
    )
    await producer.start()

    session_info = await websocket.receive_json()
    session_user = session_info["username"]
    await producer.send(topic, {"sender": session_user, "message": "has joined"})

    while True:
        try:
            await websocket.receive_json()
        except fastapi.WebSocketDisconnect:
            await producer.send(
                topic, {"sender": session_user, "message": "disconnected"}
            )
            await producer.stop()
            break


@router.post("/create_topic")
async def create_topic(topic: str):
    consumer = aiokafka.AIOKafkaConsumer(bootstrap_servers=[kafka_bootstrap_server])
    await consumer.start()
    topics = await consumer.topics()
    # print(topics)
    if topic in topics:
        await consumer.stop()
        return {"status": "topic already exists"}
    else:
        topics.add(topic)
        admin_client.create_topics(
            [kafka.admin.NewTopic(topic, num_partitions=1, replication_factor=1)]
        )
        await consumer.stop()
        return {"status": "topic created"}


@router.post("/delete_topic")
async def delete_topic(topic: str):
    consumer = aiokafka.AIOKafkaConsumer(bootstrap_servers=[kafka_bootstrap_server])
    await consumer.start()
    topics = await consumer.topics()
    await consumer.stop()
    if topic in topics:
        try:
            admin_client.delete_topics(topics=[topic])
        except aiokafka.errors.UnknownTopicOrPartitionError:
            return {"status": "topic does not exist"}
        else:
            return {"status": "topic deleted"}


@router.get("/topics")
async def get_topics():
    consumer = aiokafka.AIOKafkaConsumer(bootstrap_servers=[kafka_bootstrap_server])
    await consumer.start()
    topics = await consumer.topics()
    await consumer.stop()
    return topics
