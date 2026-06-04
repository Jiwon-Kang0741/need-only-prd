"""Deterministic Java package enforcement (package must match file path). No LLM."""

from app.llm.graph import nodes

_DAO_PATH = "src/main/java/hsc/tomms/web/cpms/edursltlst/dao/CpmsEduRsltLstDaoImpl.java"


def test_enforce_java_package_rewrites_wrong_package():
    content = "package com.example.cpms.dao;\n\nclass CpmsEduRsltLstDaoImpl {}\n"
    out = nodes._enforce_java_package(content, _DAO_PATH)
    assert "package hsc.tomms.web.cpms.edursltlst.dao;" in out
    assert "com.example.cpms" not in out


def test_enforce_java_package_inserts_when_missing():
    content = "import a.B;\ninterface CpmsEduRsltLstDao {}\n"
    out = nodes._enforce_java_package(
        content,
        "src/main/java/hsc/tomms/web/cpms/edursltlst/dao/CpmsEduRsltLstDao.java")
    assert out.startswith("package hsc.tomms.web.cpms.edursltlst.dao;")
    assert "interface CpmsEduRsltLstDao" in out


def test_enforce_java_package_noop_for_non_java():
    content = '<mapper namespace="x"></mapper>'
    assert nodes._enforce_java_package(
        content, "src/main/resources/x/CpmsEduRsltLstMapper.xml") == content
