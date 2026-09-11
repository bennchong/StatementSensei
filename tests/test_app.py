# pylint: disable=no-name-in-module
import os
from unittest.mock import patch
from uuid import uuid4
from types import SimpleNamespace

import pandas as pd
import pytest
from streamlit.proto.Common_pb2 import FileURLs
from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec

from webapp.app import app
from webapp.app import handle_file
from webapp.categorization import CategorizerConfiguration, RuleBasedCategorizer
from webapp.categorizer.constants import DEFAULT_RULES


def create_uploaded_file(file_name):
    with open(f"tests/fixtures/{file_name}", "rb") as f:
        raw_file = f.read()

    file_id = str(uuid4())

    record = UploadedFileRec(file_id=file_id, name=file_name, type="application/pdf", data=raw_file)
    upload_url = f"/_stcore/upload_file/{uuid4()}/{file_id}"
    file_urls = FileURLs(upload_url=upload_url, delete_url=upload_url)

    return UploadedFile(record, file_urls)


@pytest.fixture()
def uploaded_file():
    return create_uploaded_file("example_statement.pdf")


@pytest.fixture()
def protected_file():
    return create_uploaded_file("protected_example_statement.pdf")


def test_app(uploaded_file):
    with patch("webapp.app.get_files") as get_files:
        get_files.return_value = [uploaded_file]
        df = app()

    expected_df = pd.read_csv("tests/fixtures/example_statement.csv")

    df["date"] = pd.to_datetime(df["date"])
    df = df[["description", "amount", "date", "bank", "category"]]
    expected_df["date"] = pd.to_datetime(expected_df["date"])
    expected_df["category"] = RuleBasedCategorizer(DEFAULT_RULES).categorize(
        [
            SimpleNamespace(description=row.description, amount=row.amount)
            for row in expected_df.itertuples()
        ]
    )
    expected_df = expected_df[["description", "amount", "date", "bank", "category"]]
    pd.testing.assert_frame_equal(df, expected_df, check_dtype=False)


def test_unlock_protected(protected_file):
    os.environ["PDF_PASSWORDS"] = '["foobar123"]'
    with patch("webapp.app.get_files") as get_files:
        get_files.return_value = [protected_file]
        df = app()

    expected_df = pd.read_csv("tests/fixtures/example_statement.csv")

    df["date"] = pd.to_datetime(df["date"])
    df = df[["description", "amount", "date", "bank", "category"]]
    expected_df["date"] = pd.to_datetime(expected_df["date"])
    expected_df["category"] = RuleBasedCategorizer(DEFAULT_RULES).categorize(
        [
            SimpleNamespace(description=row.description, amount=row.amount)
            for row in expected_df.itertuples()
        ]
    )
    expected_df = expected_df[["description", "amount", "date", "bank", "category"]]

    pd.testing.assert_frame_equal(df, expected_df, check_dtype=False)


def test_handle_file_cache_includes_categorizer_configuration():
    document = type(
        "Document",
        (),
        {
            "name": "statement.pdf",
            "xref_get_key": lambda *_: (None, "document-id"),
        },
    )()
    default_configuration = CategorizerConfiguration()
    edited_rules_configuration = CategorizerConfiguration(
        rules=(("Dining", ("restaurant",)),),
    )

    with (
        patch("webapp.app.st.session_state", {}),
        patch("webapp.app.parse_bank_statement", side_effect=["default", "edited"]) as parse_statement,
    ):
        assert handle_file(document, default_configuration) == "default"
        assert handle_file(document, default_configuration) == "default"
        assert handle_file(document, edited_rules_configuration) == "edited"

    assert parse_statement.call_count == 2
