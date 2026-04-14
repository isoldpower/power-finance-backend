class ThrottleHeadersMixin:
    def get_throttles(self):
        if not hasattr(self, '_throttle_instances'):
            self._throttle_instances = super().get_throttles()
        return self._throttle_instances

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        for throttle in self.get_throttles():
            if not hasattr(throttle, 'get_headers'):
                continue
            for header, value in throttle.get_headers(request).items():
                response[header] = value

        return response