import json
import pika
from typing import Callable, Any


class RabbitMQClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str = "admin",
        password: str = "admin123",
        heartbeat: int = 600,
        blocked_connection_timeout: int = 300,
    ):
        self.host = host
        self.port = port
        self.credentials = pika.PlainCredentials(username, password)

        self.connection_params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=self.credentials,
            heartbeat=heartbeat,
            blocked_connection_timeout=blocked_connection_timeout,
        )

    def _connect(self) -> pika.BlockingConnection:
        return pika.BlockingConnection(self.connection_params)

    def publish(
        self,
        queue_name: str,
        message: dict,
        persistent: bool = True,
    ) -> None:
        """
        Publish a JSON-serializable message to a durable queue.
        """
        connection = self._connect()
        channel = connection.channel()

        channel.queue_declare(queue=queue_name, durable=True)

        body = json.dumps(message)

        properties = pika.BasicProperties(
            delivery_mode=2 if persistent else 1  # 2 = persistent
        )

        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=body,
            properties=properties,
        )

        connection.close()

    def consume(
        self,
        queue_name: str,
        callback: Callable[[dict], Any],
        prefetch_count: int = 1,
    ) -> None:
        """
        Start consuming messages from a queue.
        The callback must accept a single dict argument.
        """

        def _on_message(channel, method, properties, body):
            try:
                message = json.loads(body)
                callback(message)
                channel.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"Error processing message: {e}")
                # Do not ack -> message will be re-queued
                channel.basic_nack(
                    delivery_tag=method.delivery_tag, requeue=True
                )

        connection = self._connect()
        channel = connection.channel()

        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_qos(prefetch_count=prefetch_count)

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=_on_message,
        )

        print(f"Consuming messages from '{queue_name}'...")
        channel.start_consuming()
