from kafka import KafkaConsumer
from json import loads

consumer = KafkaConsumer(
    "numbers",
    bootstrap_servers=["localhost:9092"],
    value_deserializer=lambda x: loads(x.decode("utf-8")),
)

for message in consumer:
    print(message.value)
