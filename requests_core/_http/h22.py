import h2
import h2.connection
import h2.events
import h11

H1Response = h11.Response
H2Response = h2.events.ResponseReceived
InformationalResponse = h11.InformationalResponse

Data = h11.Data
EndOfMessage = h11.EndOfMessage

IDLE = (h11.IDLE, h2.connection.ConnectionState.IDLE)
#h2.connection.ConnectionState.CLIENT_OPEN)
CLIENT = h11.CLIENT

LocalProtocolError = h11.LocalProtocolError

class Waiting:
    pass

NEED_DATA = (h11.NEED_DATA, Waiting)

class Request:
    def __init__(self, method, target, headers):
        self.method = method
        self.target = target
        self.headers = headers

    @property
    def h11(self):
        return h11.Request(
            method=self.method,
            target=self.target,
            headers=self.headers
        )

    @property
    def h2_headers(self):
        headers = []
        headers.append((b':method', bytes(self.method, 'utf-8')))
        headers.append((b':authority', b'www.yahoo.com'))
        headers.append((b':scheme', b'https'))
        # TODO: actually do path.

        headers.append((b':path', b'/'))
        headers.append((b'user-agent', b'blah'))
        for header in self.headers:
            headers.append(header)

        # Convert headers to unicode (revisit later).
        for i, (k, v) in enumerate(headers):
            headers[i] = (k.decode('utf-8'), v.decode('utf-8'))

        return headers

from hyperframe.frame import SettingsFrame
SIZE = 4096

class Connection:
    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__()

        self.h1_connection = h11.Connection(our_role=h11.CLIENT)
        self.h2_connection = h2.connection.H2Connection()
        self.h2_connection.initiate_connection()
        self.h2_connection.update_settings({SettingsFrame.HEADER_TABLE_SIZE: SIZE})
        # self.update()
        # self.send(self.h2_connection.data_to_send(), raw=True)

        self._events = []
        self._stream = None

    @property
    def stream(self):
        if not self._stream:
            self._stream = self.h2_connection.get_next_available_stream_id()
        return self._stream

    @property
    def use_h2(self):
        return True

    @property
    def our_state(self):
        if self.use_h2:
            return self.h2_connection.state_machine.state
        else:
            return self.h1_connection.our_state

    @property
    def their_state(self):
        if self.use_h2:
            return self.h2_connection.state_machine.state
        else:
            return self.h1_connection.their_state

    def send(self, data, raw=False):
        if self.use_h2:
            if raw:
                return data
            elif isinstance(data, Request):
                self.h2_connection.send_headers(self.stream, data.h2_headers, end_stream=True)

                # self.h2_connection.send_data(1, data=b'', end_stream=False)

            elif isinstance(data, EndOfMessage):
                return self.h2_connection.data_to_send()
                # self.h2_connection.send_data(1, data=b'', end_stream=True)
            else:
                # print(dir(self.h2_connection))
                # stream = self.h2_connection.get_next_available_stream_id()
                self.h2_connection.send_data(self.stream, data)
        else:
            if isinstance(data, Request):
                r = data.h11
            return self.h1_connection.send(r)

    def receive_data(self, data):
        if self.use_h2:
            return self.h2_connection.receive_data(data)
        else:
            return [self.h1_connection.receive_data(data)]

    def record_data(self, data):
        if self.use_h2:
            self._events.extend(self.receive_data(data))

    def update(self):
        if self.use_h2:
            self.send(self.h2_connection.data_to_send(), raw=True)

    def next_event(self):
        # print(self._events)
        if self.use_h2:
            while True:
                self.record_data(self.h2_connection.data_to_send())
                try:
                    return self._events.pop()
                except IndexError:
                    self.record_data(self.h2_connection.data_to_send())
                    # return EndOfMessage()
                    try:
                        return self._events.pop()
                    except IndexError:
                        return Waiting


        else:
            return self.h1_connection.next_event()

    def start_next_cycle(self):
        if self.use_h2:
            pass
        else:
            return self.h1_connection.start_next_cycle()
