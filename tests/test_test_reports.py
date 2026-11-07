import json

import pytest

from repograph.discovery import RepositoryError
from repograph.reports import parse_report


def test_junit_counts_failures_errors_and_skips(tmp_path):
    report = tmp_path / "report.xml"
    report.write_text("""<testsuites><testsuite>
<testcase classname="test_mod.TestGroup" name="passing"/>
<testcase classname="test_mod.TestGroup" name="failing">
<failure message="assertion">trace</failure></testcase>
<testcase classname="test_mod.TestGroup" name="setup"><error message="setup failure"/></testcase>
<testcase classname="test_mod.TestGroup" name="later"><skipped/></testcase>
</testsuite></testsuites>""")
    counts, cases = parse_report(report, "pytest", tmp_path, ["test_mod.py"])
    assert counts.model_dump() == {"tests": 4, "passed": 1, "failed": 1, "errors": 1, "skipped": 1}
    assert all(case.path == "test_mod.py" for case in cases)
    assert cases[1].message == "assertion\ntrace"


@pytest.mark.parametrize("framework", ["jest", "vitest"])
def test_javascript_machine_report_counts_and_locations(tmp_path, framework):
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "numTotalTests": 3,
                "success": False,
                "testResults": [
                    {
                        "name": str(tmp_path / "x.test.js"),
                        "status": "failed",
                        "assertionResults": [
                            {"fullName": "suite passes", "status": "passed"},
                            {
                                "fullName": "suite fails",
                                "status": "failed",
                                "failureMessages": ["assertion"],
                            },
                            {"fullName": "suite pending", "status": "pending"},
                        ],
                    }
                ],
            }
        )
    )
    counts, cases = parse_report(report, framework, tmp_path, [])
    assert counts.tests == 3 and counts.passed == counts.failed == counts.skipped == 1
    assert cases[0].path == "x.test.js" and cases[1].message == "assertion"


@pytest.mark.parametrize(
    "content,framework",
    [
        ('<!DOCTYPE testsuite [<!ENTITY x "EXPAND">]><testsuite/>', "pytest"),
        ("<not-a-report/>", "pytest"),
        ('<testsuite tests="2"><testcase name="one"/></testsuite>', "pytest"),
        ('<testsuite failures="1"><testcase name="one"/></testsuite>', "pytest"),
        ("not JSON", "jest"),
        ('{"testResults":[],"numTotalTests":1}', "vitest"),
    ],
)
def test_malformed_or_inconsistent_reports_fail_closed(tmp_path, content, framework):
    report = tmp_path / "report"
    report.write_text(content)
    with pytest.raises(RepositoryError) as caught:
        parse_report(report, framework, tmp_path, [])
    assert caught.value.code == "invalid_test_report"


def test_machine_report_size_is_bounded(tmp_path):
    report = tmp_path / "report"
    report.write_bytes(b"x" * 2_000_001)
    with pytest.raises(RepositoryError) as caught:
        parse_report(report, "pytest", tmp_path, [])
    assert caught.value.code == "test_report_limit"
