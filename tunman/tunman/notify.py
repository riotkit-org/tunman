
from requests import post as http_post
from json import dumps as json_dumps
from .model import Forwarding
from .logger import Logger


class Notify:
    @staticmethod
    def notify(fw: Forwarding, msg: str):
        if not fw.validate.notify_url:
            return

        try:
            response = http_post(
                url=fw.validate.notify_url,
                data=json_dumps({
                    'text': msg
                })
            )

            assert response.status_code == 200
        except Exception as e:
            Logger.warning('Webhook error, cannot post to "%s". Details: %s' % (fw.validate.notify_url, str(e)))

    @staticmethod
    def notify_tunnel_restarted(fw: Forwarding):
        if fw.current_restart_count == 0:
            return

        Notify.notify(fw, ':warning: The tunnel "%s" was restarted, current restart count is %i' % (
            str(fw), fw.current_restart_count
        ))
