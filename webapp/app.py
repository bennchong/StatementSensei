import pandas as pd
import streamlit as st
from monopoly.pdf import MissingPasswordError, PdfDocument
from streamlit.runtime.uploaded_file_manager import UploadedFile

from webapp.constants import APP_DESCRIPTION
from webapp.categorization import CategorizationError, CategorizerConfiguration
from webapp.categorizer.constants import DEFAULT_RULES
from webapp.helpers import create_df, parse_bank_statement, show_df
from webapp.logo import logo
from webapp.models import ProcessedFile

# number of files that need to be added before progress bar appears
PBAR_MIN_FILES = 4
CATEGORIZER_LABELS = {
    "rules": "Rules",
    "gemini": "Google Gemini",
    "lmstudio": "LM Studio",
}


def app() -> pd.DataFrame:
    st.set_page_config(page_title="Statement Sensei", layout="wide")
    st.image(logo, width=450)
    st.markdown(APP_DESCRIPTION)

    configuration = get_categorizer_configuration()
    files = get_files()

    df = None
    if "df" in st.session_state:
        df = st.session_state["df"]

    if files and configuration:
        processed_files = process_files(files, configuration)

        if processed_files:
            df = create_df(processed_files)

    if df is not None:
        show_df(df)

    return df


def get_categorizer_configuration() -> CategorizerConfiguration | None:
    st.session_state.setdefault("categorizer_name", "rules")
    st.session_state.setdefault("lm_studio_url", "http://localhost:1234/v1")
    st.session_state.setdefault("lm_studio_model", "")
    st.session_state.setdefault(
        "rule_editor_data",
        [{"Category": category, "Keywords": ", ".join(keywords)} for category, keywords in DEFAULT_RULES.items()],
    )

    categorizer_name = st.selectbox(
        "Categorizer",
        options=list(CATEGORIZER_LABELS),
        format_func=CATEGORIZER_LABELS.__getitem__,
        key="categorizer_name",
    )
    rules = tuple(
        (category, tuple(keywords))
        for category, keywords in DEFAULT_RULES.items()
    )
    if categorizer_name == "lmstudio":
        st.text_input("LM Studio server URL", key="lm_studio_url")
        st.text_input("LM Studio model", key="lm_studio_model")
    elif categorizer_name == "rules":
        edited_rules = st.data_editor(
            st.session_state["rule_editor_data"],
            column_config={
                "Category": st.column_config.TextColumn(required=True),
                "Keywords": st.column_config.TextColumn(
                    help="Comma-separated keywords", required=True
                ),
            },
            hide_index=True,
            key="rule_editor",
            num_rows="dynamic",
        )
        rule_rows = (
            edited_rules.to_dict("records")
            if isinstance(edited_rules, pd.DataFrame)
            else edited_rules
        )
        rules = tuple(
            (
                str(row["Category"]).strip(),
                tuple(keyword.strip() for keyword in str(row["Keywords"]).split(",")),
            )
            for row in rule_rows
        )

    configuration = CategorizerConfiguration(
        name=categorizer_name,
        lm_studio_url=st.session_state["lm_studio_url"],
        lm_studio_model=st.session_state["lm_studio_model"],
        rules=rules,
    )
    try:
        configuration.validate()
    except CategorizationError as error:
        st.error(str(error), icon="❗")
        return None
    return configuration


def process_files(
    uploaded_files: list[UploadedFile],
    configuration: CategorizerConfiguration,
) -> list[ProcessedFile] | None:
    num_files = len(uploaded_files)
    show_pbar = num_files > PBAR_MIN_FILES

    pbar = st.progress(0, text="Processing PDFs") if show_pbar else None

    processed_files = []
    for i, file in enumerate(uploaded_files):
        if pbar:
            pbar.progress(i / num_files, text=f"Processing {file.name}")

        file_bytes = file.getvalue()
        document = PdfDocument(file_bytes=file_bytes)
        document._name = file.name

        # attempt to use passwords stored in environment to unlock
        # if no passwords in environment, then ask user for password
        if document.is_encrypted:  # pylint: disable=no-member
            try:
                document = document.unlock_document()

            except MissingPasswordError:
                document = handle_encrypted_document(document)

        if document:
            try:
                processed_file = handle_file(document, configuration)
            except CategorizationError as error:
                st.error(str(error), icon="❗")
            else:
                processed_files.append(processed_file)

    if pbar:
        pbar.empty()

    return processed_files


def handle_file(document: PdfDocument, configuration: CategorizerConfiguration) -> ProcessedFile:
    document_id = document.xref_get_key(-1, "ID")[-1]
    uuid = f"{document.name}{document_id}:{configuration.cache_signature()}"
    if uuid in st.session_state:
        return st.session_state[uuid]

    file = parse_bank_statement(document, configuration)
    st.session_state[uuid] = file
    return file


def handle_encrypted_document(document: PdfDocument) -> PdfDocument | None:
    passwords: list[str] = st.session_state.setdefault("pdf_passwords", [])

    # Try existing passwords first
    for password in passwords:
        document.authenticate(password)
        if not document.is_encrypted:  # pylint: disable=no-member
            return document

    # Prompt user for password if none of the existing passwords work
    password_container = st.empty()
    password = password_container.text_input(
        label="Password",
        type="password",
        placeholder=f"Enter password for {document.name}",
        key=document.name,
    )

    if not password:
        return None

    document.authenticate(password)

    if not document.is_encrypted:  # pylint: disable=no-member
        passwords.append(password)
        password_container.empty()
        return document

    st.error("Wrong password. Please try again.")
    return None


def get_files() -> list[UploadedFile]:
    return st.file_uploader(
        label="Upload a bank statement",
        type="pdf",
        label_visibility="hidden",
        accept_multiple_files=True,
    )


if __name__ == "__main__":
    app()
