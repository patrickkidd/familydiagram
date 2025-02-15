import os.path
import io
import logging

import pytest
import mock
import requests

from btcopilot import Engine, create_app as btcopilot_create_app
from btcopilot import engine

from tests.views.test_copilotview import view

_log = logging.getLogger(__name__)


def flask_to_requests_response(flask_response) -> requests.Response:
    response = requests.Response()
    response.status_code = flask_response.status_code
    # Flask’s test_client returns the body as bytes.
    response._content = flask_response.data
    response.headers = flask_response.headers
    response.url = "http://testserver"
    response.raw = io.BytesIO(flask_response.data)
    # (Flask response defaults to utf-8 in many cases).
    response.encoding = (
        flask_response.charset if hasattr(flask_response, "charset") else "utf-8"
    )
    return response


@pytest.fixture(autouse=True)
def btcopilot_app(tmp_path):

    VECTOR_DB_PATH = os.path.realpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "vector_db")
    )
    if not os.listdir(VECTOR_DB_PATH):
        raise RuntimeError(
            f"Integration test vector DB is empty. "
            f"Populate with `FLASK_APP=btcopilot flask ingest --data-dir {VECTOR_DB_PATH} --sources-dir <folder with pdfs>`"
        )

    app = btcopilot_create_app(instance_path=tmp_path, vector_db_path=VECTOR_DB_PATH)

    def _post(url, json=None) -> requests.Response:
        with app.test_client() as client:
            flask_response = client.post(url, json=json)
            response = flask_to_requests_response(flask_response)
            return response

    with mock.patch("fdserver.v1.CopilotClient.post", side_effect=_post):
        yield app


TIMEOUT_MS = 30000


@pytest.mark.integration
def test_copilot(view, flask_app):
    last_response = None

    def _on_response(self, response: engine.Response):
        nonlocal last_response
        last_response = response

    with mock.patch.object(Engine, "_on_response", _on_response):
        view.inputMessage("What year was the NIMH study conducted?")
        assert view.aiBubbleAdded.wait(maxMS=TIMEOUT_MS) == True
        assert (
            view.aiBubbleAdded.callArgs[0][0].property("text") == last_response.answer
        )
        _log.info(last_response.answer)
