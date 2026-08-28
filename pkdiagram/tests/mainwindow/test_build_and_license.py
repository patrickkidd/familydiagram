"""Build state and licence are marked independently.

Exempt from the citation rule: this asserts the test harness's own machinery.
"""

import pytest

import btcopilot
from pkdiagram import version
from pkdiagram.app.appcontroller import AppController


def test_the_suite_is_a_release_build_by_default(create_ac_mw, launchModals):
    ac, mw = create_ac_mw()
    assert version.IS_BETA == False

    assert launchModals == []


@pytest.mark.beta
def test_the_beta_marker_sets_the_build_and_a_licence_that_matches(
    test_activation, create_ac_mw, launchModals
):
    ac, mw = create_ac_mw()
    assert version.IS_BETA == True

    assert ac.session.activeFeatures() == [btcopilot.LICENSE_BETA]

    assert launchModals == [], "a matching licence raises nothing"


@pytest.mark.parametrize("betaBuild", [True], indirect=True)
@pytest.mark.parametrize(
    "licenseProduct", [btcopilot.LICENSE_PROFESSIONAL], indirect=True
)
def test_a_beta_build_with_a_licence_it_will_not_honour_says_so(
    test_activation, create_ac_mw, launchModals
):
    """The combination that used to freeze the suite: a beta build strips every
    non-beta licence, so the launch has no active features and asks for a beta
    licence. Recorded rather than blocking, so it is assertable."""
    ac, mw = create_ac_mw()
    assert version.IS_BETA == True

    assert ac.session.activeFeatures() == []

    assert "Beta License Required" in launchModals
