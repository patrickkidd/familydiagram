import pytest
import mock

from pkdiagram import util, Server


def test_no_callbacks_clears_replies():
    server = Server()
    allRequestsFinished = util.Condition(server.allRequestsFinished)
    server.nonBlockingRequest("GET", "/hello")
    assert allRequestsFinished.wait() == True


def test_nonBlocking_response_body():
    BODY = b"Hello, World!"

    server = Server()
    response = server.blockingRequest("GET", "/hello")
    assert response.status_code == 200
    assert response.body == BODY
