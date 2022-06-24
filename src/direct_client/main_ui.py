import asyncio
from email import message
import json
import kafka

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QUrl, QRunnable, QThread
from qasync import QEventLoop
import aiokafka

from ui_lib import Ui_MainWindow


class Receiver(QtCore.QObject):
    message_received = QtCore.pyqtSignal(dict)
    is_running = True

    def __init__(self, server, topic):
        super().__init__()
        self.consumer = aiokafka.AIOKafkaConsumer(
            topic,
            bootstrap_servers=[server],
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )
        asyncio.ensure_future(self.receiving_loop())

    async def receiving_loop(self):
        await self.consumer.start()
        while self.is_running:
            msg = await self.consumer.getone()
            if msg is not None:
                self.message_received.emit(msg.value)
        await self.consumer.stop()

    def stop(self):
        self.message_received.disconnect()
        self.is_running = False


class GUI(Ui_MainWindow, QtWidgets.QMainWindow):
    kafka_server = "127.0.0.1:9092"
    chat_topic = ""
    username = None

    receive_thread, send_thread = None, None

    def __init__(self) -> None:
        super().__init__()

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        self.chatBar.setEnabled(False)
        self.chatContent.setReadOnly(True)
        self.chatBar.returnPressed.connect(self.on_message_sent)
        self.topicList.itemClicked.connect(self.on_topic_selected)
        self.createTopicBtn.clicked.connect(self.on_create_topic)
        self.actionChange_Username.triggered.connect(self.on_change_username)
        self.actionChange_Server.triggered.connect(self.on_change_server)
        self.actionExit.triggered.connect(MainWindow.close)

        self.on_load()

    def retranslateUi(self, MainWindow):
        super().retranslateUi(MainWindow)

    def on_load(self):
        if self.username is None:
            self.username, ok = QtWidgets.QInputDialog.getText(
                self, "Change Username", "Enter username:"
            )
            if not ok:
                self.username = "Anonymous"

        self.kafka_server, ok = QtWidgets.QInputDialog.getText(
            self,
            "Change Server",
            "Enter server address (host:port). Cancel to use localhost:",
        )
        if not ok:
            self.kafka_server = "127.0.0.1:9092"
        else:
            if ":" not in self.kafka_server:
                self.kafka_server += ":9092"

        temp_consumer = kafka.KafkaConsumer(
            bootstrap_servers=[self.kafka_server],
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )
        topics = temp_consumer.topics()
        temp_consumer.close()
        for topic in topics:
            self.topicList.addItem(topic)

        if self.send_thread is not None:
            asyncio.get_running_loop().run_until_complete(self.send_thread.stop())
            del self.send_thread

        asyncio.ensure_future(self._start_sender_thread())

    async def _start_sender_thread(self):
        self.send_thread = aiokafka.AIOKafkaProducer(
            bootstrap_servers=[self.kafka_server],
            value_serializer=lambda x: json.dumps(x).encode("utf-8"),
        )
        await self.send_thread.start()

    def on_create_topic(self):
        topic, ok = QtWidgets.QInputDialog.getText(
            self, "Create Topic", "Enter topic name:"
        )
        if ok:
            self.topicList.addItem(topic)

    def on_topic_selected(self):
        if self.chat_topic == self.topicList.currentItem().text():
            return

        self.chat_topic = self.topicList.currentItem().text()
        if self.receive_thread is not None:
            self.receive_thread.stop()
            asyncio.ensure_future(
                self.send_thread.send(
                    self.chat_topic,
                    {"username": self.username, "message": "has left the chat"},
                )
            )

        self.chatContent.clear()
        self.chatBar.setPlaceholderText(f"Send a message to {self.chat_topic}")
        self.chatBar.setEnabled(True)

        self.receive_thread = Receiver(self.kafka_server, self.chat_topic)
        self.receive_thread.message_received.connect(self.on_message_received)

        asyncio.ensure_future(
            self.send_thread.send(
                self.chat_topic,
                {
                    "username": self.username,
                    "message": f'has joined the topic "{self.chat_topic}"',
                },
            )
        )

    def on_message_received(self, message):
        self.chatContent.appendPlainText(
            message["username"] + ": " + message["message"]
        )

    def on_message_sent(self):
        message = self.chatBar.text()
        self.chatBar.setText("")
        asyncio.ensure_future(
            self.send_thread.send(
                self.chat_topic, {"username": self.username, "message": message}
            )
        )

    def on_change_username(self):
        self.username, ok = QtWidgets.QInputDialog.getText(
            self, "Change Username", "Enter username:"
        )

    def on_change_server(self):
        self.kafka_server, ok = QtWidgets.QInputDialog.getText(
            self, "Change Server", "Enter server address:"
        )
        if ok:
            self.on_load()


def main():
    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        ui = GUI()
        ui.setupUi(MainWindow)
        MainWindow.show()
        loop.run_forever()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
