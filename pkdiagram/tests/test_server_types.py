from pkdiagram import util
from pkdiagram.server_types import Server
from pkdiagram.pyqt import QSslError


def test_no_callbacks_clears_replies():
    server = Server()
    allRequestsFinished = util.Condition(server.allRequestsFinished)
    server.nonBlockingRequest("GET", "/hello")
    assert allRequestsFinished.wait() == True


def test_nonBlocking_response_body():
    BODY = b"Hello, World!"

    server = Server()
    response = server.blockingRequest("GET", "/health")
    assert response.status_code == 200
    assert response.body == BODY


def test_ssl_errors_handler_receives_errors_parameter(caplog):
    server = Server()
    reply = server.nonBlockingRequest("GET", "/hello")
    ssl_error = QSslError()
    errors = [ssl_error]
    reply.sslErrors.emit(errors)
    assert "SSL Errors:" in caplog.text
    assert len(server._repliesInFlight) == 1
