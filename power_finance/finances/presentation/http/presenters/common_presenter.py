from dataclasses import dataclass


@dataclass(frozen=True)
class MessageResultInfo:
    message: str


class CommonHttpPresenter:
    @staticmethod
    def present_message_result(info: MessageResultInfo) -> dict[str, str]:
        return {
            'message': info.message
        }
