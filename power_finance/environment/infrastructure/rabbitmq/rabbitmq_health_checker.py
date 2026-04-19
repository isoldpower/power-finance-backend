import aio_pika
from aio_pika import exceptions
from pika import ConnectionParameters

from environment.application.interfaces import ServiceHealthChecker
from environment.domain.entities import HealthProbeStatus


class RabbitMQHealthChecker(ServiceHealthChecker):
    def __init__(self, connection: ConnectionParameters):
        self._rabbitmq_connection = connection

    async def health_status(self) -> str:
        amqp_connection = None
        try:
            amqp_connection = await aio_pika.connect_robust(
                host=self._rabbitmq_connection.host,
                port=self._rabbitmq_connection.port,
                login=self._rabbitmq_connection.credentials.username,
                password=self._rabbitmq_connection.credentials.password,
            )
            return HealthProbeStatus.OK.value
        except exceptions.AMQPConnectionError as e:
            return f"Error connecting to RabbitMQ. {str(e)}"
        finally:
            if amqp_connection is not None and not amqp_connection.is_closed:
                await amqp_connection.close()
