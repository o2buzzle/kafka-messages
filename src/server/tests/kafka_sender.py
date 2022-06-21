from math import prod
from multiprocessing.sharedctypes import Value
from time import sleep
import kafka
from json import dumps

producer = kafka.KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda x: dumps(x).encode("utf-8"),
)
for e in range(1000):
    data = {"number": e}
    producer.send("numbers", value=data)
    sleep(5)

producer.flush()
