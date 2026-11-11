"""Test di regressione per il parsing delle Job Description.

Il parsing e' la parte piu' fragile dell'app: si basa su euristiche sul testo
libero, quindi ogni modifica va coperta da un caso noto.

    pip install -r requirements-dev.txt
    pytest -q
"""

import importlib.util
import os
import sys

import pytest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "app.py")


def _load_app():
    """Carica app.py come modulo, senza eseguire il rendering Streamlit."""
    spec = importlib.util.spec_from_file_location("career_optimizer_app", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


app = _load_app()


# --- Rilevamento lingua ----------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("We are hiring a Finance Director. The role requires IFRS knowledge.",
     "en"),
    ("Stiamo assumendo un Direttore Finanziario. Il ruolo richiede IFRS.",
     "it"),
    ("Posizione: CFO. Azienda: Initech. Cerchiamo un Direttore Finanziario.",
     "it"),
    ("Si cerca un Responsabile Finanza presso Marzotto Group. Offriamo crescita.",
     "it"),
    ("Ricerca Head of Finance per il Gruppo Monte dei Paschi. Requisiti: IFRS.",
     "it"),
    ("The client, Swiss Re Global, seeks a Head of Finance to lead transformation.",
     "en"),
])
def test_detect_language(text, expected):
    assert app.detect_language(text) == expected


# --- Nome aziendale --------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    # Trigger classici
    ("We are hiring a Finance Director at Acme Corporation. Join us!",
     "Acme Corporation"),
    ("Stiamo assumendo un Direttore Finanziario presso Alfa S.p.A. e leader.",
     "Alfa S.p.A."),
    # Etichette esplicite
    ("Company: Initech. Position: CFO.", "Initech"),
    ("Azienda: Initech. Cerchiamo un Direttore Finanziario.", "Initech"),
    # Nome in testa alla frase
    ("Acme Corporation is hiring a Finance Director. About Acme: we innovate.",
     "Acme Corporation"),
    ("Banca Intesa Sanpaolo ricerca un CFO. Offerta di lavoro a Milano.",
     "Banca Intesa Sanpaolo"),
    # Nome da solo in cima all'annuncio
    ("Acme Corporation\nWe are hiring a Head of Finance.", "Acme Corporation"),
    ("Banca Intesa Sanpaolo\nSiamo alla ricerca di un Direttore Finanziario.",
     "Banca Intesa Sanpaolo"),
    # Casi particolari
    ("About us: Globex International, a leading provider.", "Globex International"),
    ("The client, Swiss Re Global, seeks a Head of Finance.", "Swiss Re Global"),
    ("Make an impact with Initech. Senior Finance Manager role.",
     "Initech"),
    ("We are hiring at AT&T a Vice President of Finance.", "AT&T"),
    ("Job Description: Finance Director at Initech. Great team.",
     "Initech"),
    ("Ricerca Head of Finance per il Gruppo Monte dei Paschi. Requisiti: IFRS.",
     "Gruppo Monte dei Paschi"),
])
def test_extract_company(text, expected):
    assert app.extract_company(text) == expected


def test_extract_company_never_returns_role_words():
    """Il nome non deve mai essere una parola che descrive il ruolo."""
    for text in [
        "Job Description: Finance Director. Great team, great mission.",
        "We are hiring. Position: Head of Finance.",
        "Il testo dell'annuncio e troppo breve.",
    ]:
        company = app.extract_company(text)
        if company == "Company":          # fallback neutro, verificato a parte
            continue
        words = [w.lower() for w in company.split()]
        assert not all(w in app.ROLE_WORDS for w in words), company


def test_extract_company_falls_back_instead_of_guessing():
    """Senza indizi il fallback resta neutro, non un nome inventato."""
    assert app.extract_company("Generic description of a role.") == "Company"


# --- Titolo del ruolo ------------------------------------------------------

@pytest.mark.parametrize("text,lang,expected", [
    ("We are hiring a Finance Director at Acme.", "en", "Finance Director"),
    ("Company: Initech. Position: CFO.", "en", "CFO"),
    ("We want a VP Finance to own cloud transformation.", "en", "VP Finance"),
    ("The client seeks a Head of Finance to lead transformation.", "en",
     "Head of Finance"),
    ("Role: Finance Director. About Acme: innovation.", "en", "Finance Director"),
    ("Stiamo assumendo un Direttore Finanziario presso Alfa S.p.A.", "it",
     "Direttore Finanziario"),
    ("Posizione: CFO. Azienda: Initech.", "it", "CFO"),
    ("Si cerca un Responsabile Finanza presso Marzotto Group.", "it",
     "Responsabile Finanza"),
    ("Ricerca Head of Finance per il Gruppo Monte dei Paschi.", "it",
     "Head of Finance"),
])
def test_extract_role(text, lang, expected):
    assert app.extract_role(text, lang) == expected


def test_extract_role_prefers_hiring_context():
    """Il titolo nella frase di assunzione vince su un riferimento casuale."""
    text = ("We are hiring a Finance Director. You will report to the Head of "
            "Finance and collaborate with the CFO.")
    assert app.extract_role(text, "en") == "Finance Director"


def test_extract_role_ignores_headquarters():
    """'Head' dentro 'Headquarters' non deve generare un titolo."""
    text = "Company: Initech. Headquarters: Milan. Position: Finance Manager."
    assert app.extract_role(text, "en") == "Finance Manager"


# --- Key value -------------------------------------------------------------

def test_key_value_matches_without_accents():
    """Gli annunci italiani spesso sono scritti senza accenti."""
    text = "Siamo alla ricerca. L'azienda punta sulla sostenibilita e sulla crescita."
    _, _, char = app.extract_info(text, "it")
    assert char == "sostenibilità"


def test_key_value_defaults_to_mission():
    assert app.extract_info("A job with no keywords whatsoever.", "en")[2] == "mission"
    assert app.extract_info("Un annuncio senza parole chiave.", "it")[2] == "missione"


# --- Generazione documenti --------------------------------------------------

def test_create_docs_generates_valid_docx():
    import io

    from docx import Document

    profile = app.yaml.safe_load(app.PROFILE_YAML)
    cl, cv = app.create_docs(profile, "en", "Acme Corporation", "Finance Director",
                             "innovation")
    for buffer in (cl, cv):
        payload = buffer.getvalue()
        assert payload[:2] == b"PK"          # ZIP valido
        doc = Document(io.BytesIO(payload))
        assert doc.paragraphs
    assert "Acme Corporation" in \
        "\n".join(p.text for p in Document(io.BytesIO(cl.getvalue())).paragraphs)
