import os.path
import logging

import pytest
import mock
from langchain.docstore.document import Document

from btcopilot.pro.copilot import Engine, Response
from pkdiagram import util
from pkdiagram.models import SearchModel
from pkdiagram.models.copilotengine import CopilotEngine, formatSources
from pkdiagram.app import Session
from pkdiagram.scene import Person, Event, Marriage

from btcopilot.tests.pro.copilot.conftest import llm_response

_log = logging.getLogger(__name__)


@pytest.fixture
def searchModel(scene):
    _searchModel = SearchModel()
    _searchModel.scene = scene
    yield _searchModel


@pytest.fixture
def copilot(test_session, scene, searchModel):
    session = Session()
    session.init(sessionData=test_session.account_editor_dict())
    copilot = CopilotEngine(session, searchModel)
    copilot.setScene(scene)
    yield copilot


def test_ask(copilot, llm_response):

    RESPONSE_1 = "Hello back"
    PASSAGE_1 = "Some content 1"
    PASSAGE_2 = "Some content 2"
    TITLE_1 = "Book 1"
    TITLE_2 = "Book 2"
    AUTHORS_1 = "Author 1"
    AUTHORS_2 = "Author 2"

    responseReceived = util.Condition(copilot.responseReceived)

    with llm_response(
        RESPONSE_1,
        sources=[
            Document(
                page_content=PASSAGE_1,
                metadata={
                    "fd_file_name": "bleh1.pdf",
                    "fd_title": TITLE_1,
                    "fd_authors": AUTHORS_1,
                },
            ),
            Document(
                page_content=PASSAGE_2,
                metadata={
                    "fd_file_name": "bleh2.pdf",
                    "fd_title": TITLE_2,
                    "fd_authors": AUTHORS_2,
                },
            ),
        ],
    ):
        copilot.ask("Hello there")

    responseData = {
        "response": RESPONSE_1,
        "sources": [
            {"passage": PASSAGE_1, "fd_title": TITLE_1, "fd_authors": AUTHORS_1},
            {"passage": PASSAGE_2, "fd_title": TITLE_2, "fd_authors": AUTHORS_2},
        ],
    }

    assert responseReceived.wait() == True
    assert responseReceived.callArgs[0][0] == RESPONSE_1
    assert responseReceived.callArgs[0][1] == formatSources(responseData["sources"])
    assert responseReceived.callArgs[0][2] == 2

    RESPONSE_2 = "I'm here"

    responseReceived.reset()
    with llm_response(RESPONSE_2):
        copilot.ask("Say somethign else")
    assert responseReceived.wait() == True
    assert responseReceived.callArgs[0][0] == RESPONSE_2
    assert responseReceived.callArgs[0][1] == formatSources([])
    assert responseReceived.callArgs[0][2] == 0


def test_ask_with_tags(scene, qmlEngine, copilot, llm_response):
    TAG_1 = "tag1"

    responseReceived = util.Condition(copilot.responseReceived)
    person_a, person_b = Person(name="Alice"), Person(name="Bob")
    marriage = Marriage(person_a, person_b)
    scene.addItems(person_a, person_b, marriage)
    events = [
        Event(
            dateTime=util.Date(2021, 1, 1),
            description="Bonded",
            people=["Alice", "Bob"],
            tags=[TAG_1],
            anxiety="down",
            symptom="up",
        ),
        Event(
            dateTime=util.Date(2022, 1, 1),
            description="First argument",
            people=["Alice", "Bob"],
            tags=[TAG_1],
            anxiety="up",
        ),
    ]
    scene.addItems(*events)
    qmlEngine.searchModel.tags = [TAG_1]
    with llm_response("Here is an answer"):
        copilot.ask("Hello there", includeTags=True)
    assert responseReceived.wait() == True
    assert responseReceived.callArgs[0][0] == "Here is an answer"


def test_server_down(server_down, copilot):
    serverDown = util.Condition(copilot.serverDown)
    with server_down():
        copilot.ask("Here we going?")
    assert serverDown.wait() == True


def test_server_error(copilot):
    serverError = util.Condition(copilot.serverError)
    with mock.patch.object(Engine, "ask", side_effect=ValueError("Some exception")):
        copilot.ask("Here we going?")
    assert serverError.wait() == True


TIMEOUT_MS = 30000


@pytest.mark.vector_db(
    path=os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "btcopilot",
            "instance",
            "vector_db",
        )
    )
)
@pytest.mark.integration
def test_full_stack(flask_app, copilot):
    last_response = None

    def _on_response(self, response: Response):
        nonlocal last_response
        last_response = response

    responseReceived = util.Condition(copilot.responseReceived)

    with mock.patch.object(Engine, "_on_response", _on_response):
        copilot.ask("What year was the NIMH study conducted?")
        assert responseReceived.wait(maxMS=TIMEOUT_MS) == True
        assert responseReceived.callArgs[0][0] == last_response.answer
        _log.info(last_response.answer)
