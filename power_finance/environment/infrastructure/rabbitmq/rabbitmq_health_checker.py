from pika import ConnectionParameters, BlockingConnection, exceptions

from environment.application.interfaces import ServiceHealthChecker
from environment.domain.entities import HealthProbeStatus


class RabbitMQHealthChecker(ServiceHealthChecker):
    def __init__(self, connection: ConnectionParameters):
        self._rabbitmq_connection = connection

    def health_status(self) -> str:
        amqp_connection = None
        try:
            amqp_connection = BlockingConnection(self._rabbitmq_connection)

            if amqp_connection.is_open:
                return HealthProbeStatus.OK.value
            return "Error connecting to RabbitMQ. Connection is closed."
        except exceptions.AMQPConnectionError as e:
            return f"Error connecting to RabbitMQ. {str(e)}"
        finally:
            if amqp_connection is not None and amqp_connection.is_open:
                amqp_connection.close()
