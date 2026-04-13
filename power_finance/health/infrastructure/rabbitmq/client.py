from pika import ConnectionParameters, PlainCredentials


def build_rabbitmq_connection(
        host: str,
        port: int,
        username: str,
        password: str,
) -> ConnectionParameters:
    return ConnectionParameters(
        host=host,
        port=port,
        socket_timeout=5,
        credentials=PlainCredentials(
            username=username,
            password=password
        ),
    )