"""Regression tests: Java imports must match pom.xml (no false positives from broad groupId prefixes)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config import settings
from app.llm.agents import static_check
from app.llm.codegen_context import invalidate_pom_cache
from app.models import GeneratedFile

POI_JAVA = """package biz.test;
import org.apache.poi.ss.usermodel.Workbook;
public class T { }
"""


@pytest.fixture(autouse=True)
def _clear_pom_cache():
    invalidate_pom_cache()
    yield
    invalidate_pom_cache()


def test_poi_rejected_when_pom_only_has_org_apache_maven():
    """org.apache.maven.* must not imply org.apache.poi (two-segment prefix heuristic)."""
    fake_lines = ["  - org.apache.maven.surefire:surefire-junit-platform:3.2.5"]
    fake_gids = {"org.springframework.boot", "org.apache.maven.surefire", "pfy"}

    with patch("app.llm.codegen_context._parse_pom_xml", return_value=(fake_lines, fake_gids)):
        invalidate_pom_cache()
        gf = GeneratedFile(
            file_path="biz/test/T.java",
            file_type="service_impl",
            layer="backend",
            content=POI_JAVA,
        )
        issues = static_check([gf])

    assert any("NOT declared in pom" in (i.get("issue") or "") for i in issues), issues


def test_poi_rejected_skeleton_docker_pom():
    """Default docker skeleton pom has no Apache POI coordinate."""
    with patch.object(settings, "CODEGEN_DEPLOY_MODE", "docker"):
        invalidate_pom_cache()
        gf = GeneratedFile(
            file_path="biz/test/T.java",
            file_type="service_impl",
            layer="backend",
            content=POI_JAVA,
        )
        issues = static_check([gf])

    assert any("NOT declared in pom" in (i.get("issue") or "") for i in issues), issues
