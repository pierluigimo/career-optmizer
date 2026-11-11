import streamlit as st
import yaml
import re
import os
import unicodedata
import urllib.parse
from docx import Document
from docx.shared import Pt
import io
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Strategic Career Optimizer", page_icon="🚀", layout="wide")

# --- DATI MASTER (ESTRATTI DAI TUOI PDF) ---
# Incorporati qui per evitare problemi di lettura file sul cloud
PROFILE_YAML = """
meta:
  user_id: "pierluigi_monaco"
  role_type: "Strategic Finance Executive"
  contact_info:
    phone: "+39 348 8513668"
    email: "pierluigimonaco2@gmail.com"
    location: "Milano"
    linkedin: "linkedin.com/in/pierluigimonaco"

en:
  summary: "Strategic Finance Executive with 20+ years of global experience leading transformation, financial governance and operational optimization. Delivered 15% OPEX reduction through $9M rebate harmonization and stabilized operations in volatile markets. Influenced $6B+ in investments and partnered with C-level leaders."
  core_projects:
    - title: "Subscription Model Transformation"
      company: "OpenText"
      impact: "Generated $6.9M new subscription business & reduced churn from 20% to 10%."
    - title: "Global Financing Policy"
      company: "Micro Focus"
      impact: "Designed policy for $6B worldwide operations."
  capability_themes:
    - id: "strategic_finance"
      name: "Strategic Finance & Executive Partnering"
      keywords: ["C-Level", "Stakeholder", "Strategy", "Governance"]
      evidence:
        - "Managed $205M revenue and $95M cost portfolio across EMEA, NA, APAC."
        - "Influenced $6B+ global investment decisions."
        - "Supported 425+ FTEs globally."
    - id: "transformation"
      name: "Cloud / Subscription Transformation"
      keywords: ["SaaS", "Subscription", "Recurring Revenue", "Cloud"]
      evidence:
        - "Generated $6.9M new subscription business."
        - "Reduced contract loss rate from 20% to 10%."
        - "Transitioned financial models impacting $58M revenue base."
    - id: "cost_optimization"
      name: "Cost Optimization & Operational Excellence"
      keywords: ["Cost Reduction", "Efficiency", "OPEX", "Shared Services"]
      evidence:
        - "Achieved 15% OPEX reduction via process harmonization."
        - "Delivered 10% operational cost reduction across 3 regions."
  education:
    - "CFO Program (Ongoing) - Business School Il Sole 24 Ore (2025)"
    - "Master in Finance, Administration and Control - Business School Il Sole 24 Ore"
    - "Bachelor's Degree in Economics - Università Cattolica del Sacro Cuore"
  skills:
    hard: ["Financial Modeling", "IFRS/US GAAP", "SaaS Metrics (ARR/MRR)", "Risk Management"]
    tools: ["SAP", "OneStream", "Hyperion", "Essbase", "Excel (Advanced)"]

it:
  summary: "Strategic Finance Executive con oltre 20 anni di esperienza globale nella guida di progetti di trasformazione, governance finanziaria e ottimizzazione operativa. Ho conseguito una riduzione del 15% dei costi operativi (OPEX) e supportato oltre 4 milioni di dollari in nuovi ricavi cloud."
  core_projects:
    - title: "Trasformazione Modello Subscription"
      company: "OpenText"
      impact: "Generato $6.9M di nuovo business e ridotto il tasso di perdita dal 20% al 10%."
    - title: "Policy Globale di Finanziamento"
      company: "Micro Focus"
      impact: "Policy applicata su operazioni da oltre $6B a livello mondiale."
  capability_themes:
    - id: "strategic_finance"
      name: "Finanza Strategica & Executive Partnering"
      keywords: ["Direzione", "Strategia", "Stakeholder", "Governance"]
      evidence:
        - "Gestione portafoglio ricavi $205M e costi $95M su EMEA, NA, APAC."
        - "Advisor strategico per decisioni di investimento globali da oltre $6B."
    - id: "transformation"
      name: "Trasformazione Cloud / Subscription"
      keywords: ["SaaS", "Subscription", "Cloud", "Ricavi Ricorrenti"]
      evidence:
        - "Generato $6.9M in nuovo business subscription."
        - "Ridotto il tasso di perdita contrattuale dal 20% al 10%."
    - id: "cost_optimization"
      name: "Eccellenza Operativa"
      keywords: ["Riduzione Costi", "Efficienza", "OPEX"]
      evidence:
        - "Riduzione del 15% dei costi operativi (OPEX) tramite armonizzazione processi."
        - "-10% sui costi operativi in tre regioni."
  education:
    - "CFO Program (In corso) - Business School Il Sole 24 Ore (2025)"
    - "Master in Finanza, Amministrazione e Controllo - Business School Il Sole 24 Ore"
    - "Laurea in Economia e Gestione Aziendale - Università Cattolica del Sacro Cuore"
  skills:
    hard: ["Modellazione Finanziaria", "IFRS/US GAAP", "Metriche SaaS", "Gestione Rischio"]
    tools: ["SAP", "OneStream", "Hyperion", "Essbase", "Excel (Avanzato)"]
"""

# --- LOGICA DI BUSINESS ---

# I marker sono parole intere (token), non sottostringhe: "per" in inglese
# ("per annum") non deve più sbagliare la lingua, e "e" italiano non deve
# essere confuso con una lettera dentro un'altra parola.
EN_MARKERS = {
    'the', 'and', 'to', 'of', 'with', 'we', 'are', 'our', 'will', 'you', 'your',
    'role', 'team', 'company', 'experience', 'required', 'requirements', 'skills',
    'responsibilities', 'salary', 'benefits', 'apply', 'about', 'who', 'seeking',
    'hiring', 'position', 'join', 'us', 'work', 'candidate', 'employer', 'job',
    'business', 'opportunity', 'including', 'knowledge', 'ability', 'must',
    'preferred', 'reports', 'reporting', 'lead', 'manage', 'strategy',
}

IT_MARKERS = {
    'il', 'lo', 'gli', 'la', 'le', 'di', 'del', 'della', 'dei', 'delle', 'nel',
    'nella', 'alla', 'alle', 'un', 'una', 'che', 'per', 'con', 'e', 'si', 'siamo',
    'stiamo', 'cerca', 'cerchiamo', 'ricerca', 'ricercasi', 'posizione', 'ruolo',
    'azienda', 'requisiti', 'competenze', 'esperienza', 'offriamo', 'offerta',
    'contratto', 'settore', 'responsabilita', 'assumiamo', 'profilo', 'candidatura',
}


def _strip_accents(text):
    """Rimuove i diacritici: 'sostenibilita' deve combaciare con 'sostenibilità'."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _norm(text):
    """Versione normalizzata e case-insensitive per i confronti testuali."""
    return _strip_accents(text.lower())


def detect_language(text):
    """Rileva la lingua dell'annuncio contando i marker come parole intere."""
    tokens = re.findall(r"[a-zA-Zà-ÿ']+", _norm(text))
    counts = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    score_en = sum(counts.get(w, 0) for w in EN_MARKERS)
    score_it = sum(counts.get(w, 0) for w in IT_MARKERS)
    if score_it > score_en:
        return 'it'
    if score_en > score_it:
        return 'en'
    # Pareggio: una JD italiana senza marker espliciti si riconosce dai diacritici
    # o da parole che non esistono in inglese.
    if re.search(r"[àèéìòù]", text.lower()) and re.search(
            r"\b(siamo|stiamo|cerchiamo|ricerca|azienda|offriamo)\b", _norm(text)):
        return 'it'
    return 'en'


# Titoli riconosciuti, per lingua. L'ordine conta: i titoli piu' specifici
# vengono testati prima di quelli generici.
ROLE_PATTERNS = {
    'en': [
        (r"\bchief financial officer\b", "Chief Financial Officer"),
        (r"\bcfo\b", "CFO"),
        (r"\bfinance director\b", "Finance Director"),
        (r"\bdirector of finance\b", "Finance Director"),
        (r"\bgroup financial controller\b", "Group Financial Controller"),
        (r"\bhead of finance\b", "Head of Finance"),
        (r"\bhead of financial control\b", "Head of Financial Control"),
        (r"\bvice president of finance\b", "VP Finance"),
        (r"\bvp,? (?:of )?finance\b", "VP Finance"),
        (r"\bsenior finance manager\b", "Senior Finance Manager"),
        (r"\bfinance manager\b", "Finance Manager"),
        (r"\bfinancial controller\b", "Financial Controller"),
    ],
    'it': [
        (r"\bdirettore amministrativo e finanziario\b", "Direttore Amministrativo e Finanziario"),
        (r"\bdirettore finanziario\b", "Direttore Finanziario"),
        (r"\bdirettore finance\b", "Direttore Finanziario"),
        (r"\bresponsabile amministrativo e finanziario\b", "Responsabile Amministrativo e Finanziario"),
        (r"\bresponsabile finanza\b", "Responsabile Finanza"),
        (r"\bresponsabile finance\b", "Responsabile Finanza"),
        (r"\bchief financial officer\b", "CFO"),
        (r"\bcfo\b", "CFO"),
        (r"\bfinance director\b", "Finance Director"),
        (r"\bhead of finance\b", "Head of Finance"),
        (r"\bvice president of finance\b", "VP Finance"),
        (r"\bvp,? (?:of )?finance\b", "VP Finance"),
        (r"\bsenior finance manager\b", "Senior Finance Manager"),
        (r"\bfinance manager\b", "Finance Manager"),
        (r"\bfinancial controller\b", "Financial Controller"),
    ],
}

# Parole che segnalano che l'annuncio sta descrivendo il ruolo, non l'azienda.
ROLE_WORDS = {
    'finance', 'financial', 'director', 'head', 'vp', 'vice', 'president', 'cfo',
    'chief', 'officer', 'manager', 'senior', 'junior', 'analyst', 'controller',
    'role', 'position', 'job', 'team', 'company', 'vacancy', 'description',
    'requisition', 'opportunity', 'candidate', 'profile', 'titolo', 'posizione',
    'ruolo', 'cerca', 'cerchiamo', 'ricerca', 'assumiamo', 'stiamo',
    'the', 'a', 'an', 'of', 'and', 'or', 'to', 'at', 'on', 'in', 'for', 'with',
    'we', 'our', 'you', 'your', 'they', 'their', 'this', 'that', 'who', 'what',
    'il', 'lo', 'la', 'le', 'gli', 'un', 'una', 'e', 'di', 'da', 'per', 'con',
    'nel', 'della', 'delle', 'dei', 'del', 'siamo', 'stiamo', 'cerca',
    'cerchiamo', 'ricerca', 'azienda', 'requisiti', 'competenze', 'esperienza',
    'si', 'siamo', 'offriamo', 'offerta', 'settore', 'gruppo',
    'about', 'us', 'join', 'make', 'impact', 'careers', 'career', 'great',
    'mission', 'offer', 'full', 'time', 'part', 'permanent', 'contract',
    'temporary', 'remote', 'hybrid', 'location', 'based', 'please', 'apply',
    'who', 'what', 'why', 'will', 'work', 'working', 'know', 'able', 'strong',
    # Ruoli in italiano
    'direttore', 'direttori', 'finanziario', 'finanziaria', 'finanziari',
    'responsabile', 'amministrativo', 'amministrativa', 'contabile',
    'commerciale', 'qualita', 'tecnico', 'personale', 'marketing', 'gruppo',
}

# Suffissi societari: se presenti il candidato e' molto probabilmente un'azienda.
CORPORATE_SUFFIX = re.compile(
    r"\b(inc|ltd|llc|plc|corp|corporation|company|co|group|group|holding|"
    r"holdings|s\.?p\.?a\.?|s\.?r\.?l\.?|b\.?v\.?|n\.?v\.?|gmbh|ag|s\.?a\.?|"
    r"partners|technologies|solutions|services)\b",
    re.IGNORECASE)

# Sigle societarie che vanno conservate con il punto finale ("Alfa S.p.A.").
LEGAL_FORM_RE = re.compile(
    r"\b(s\.?p\.?a|s\.?r\.?l|b\.?v|n\.?v|inc|ltd|plc|corp)$", re.IGNORECASE)

# Token che possono comporre un nome aziendale. Accetta acronimi e sigle
# societarie come "S.p.A.", "AT&T", "BHP".
_NAME_TOKEN = r"[A-Z][\w&'’]*(?:\.[A-Za-z][\w&'’]*)*"
# Connettivi ammessi dentro un nome ("Bank of America", "Banca di Roma").
# "and"/"e" sono esclusi per non unire due nomi aziendi diversi.
# L'ordine conta: le alternative piu' lunghe vanno prima, altrimenti "dei"
# viene letto come "de" e il nome si trappa.
_NAME_CONNECTOR = r"(?:of|della|delle|dei|del|di|de|la|le|the)"
_NAME_RE = re.compile(
    r"((?:%s)(?:\s+(?:%s|%s))*)" % (_NAME_TOKEN, _NAME_TOKEN, _NAME_CONNECTOR))

# Articoli da rimuovere davanti al nome ("il Gruppo ..." -> "Gruppo ...").
_LEADING_ARTICLE_RE = re.compile(
    r"^(?:the|il|lo|la|i|gli|le|l'|un|una|our|your)\s+", re.IGNORECASE)
# Connettivi da rimuovere in coda ("Alfa S.p.A. e" -> "Alfa S.p.A.").
_TRAILING_CONNECTOR_RE = re.compile(
    r"\s+(?:of|and|de|del|di|della|dei|delle|la|le|the|e|&)$", re.IGNORECASE)

# Frasi che introducono il nome dell'azienda. "at" e "presso" coprono la gran
# parte dei casi reali; le altre sono fallback.
EN_TRIGGERS = [r"about\s+(?:us|the\s+company)\s*:?", r"at", r"with", r"about",
               r"join", r"from"]
IT_TRIGGERS = [r"presso", r"da", r"per", r"di"]

# Verbi che, dopo un nome, indicano che quel nome e' l'azienda
# ("Acme Corporation is hiring...", "Banca Intesa ricerca...").
COMPANY_VERB_RE = re.compile(
    r"^\s*(?:is|seeks?|seeking|looking|searches|searching|has|have|offers?|"
    r"offre|offerta|ricerca|cerca|cerchiamo|assume|sta|è|e')\b",
    re.IGNORECASE)

# Etichette esplicite: "Company: Acme", "Azienda: Initech".
COMPANY_LABEL_RE = re.compile(
    r"(?:^|\n|\s)(?:company|azienda|employer|datore di lavoro|organizzazione|"
    r"societa|società|firma|business unit)\s*[:\-–]\s*(.+)",
    re.IGNORECASE)

# "The client, Swiss Re Global, is hiring..." / "Il cliente, Alfa, cerca..."
CLIENT_LABEL_RE = re.compile(
    r"\b(?:client|cliente|azienda|company)\s*,\s*(.+)", re.IGNORECASE)

# Frasi che indicano che il titolo trovato e' il ruolo cercato.
HIRING_CUES = re.compile(
    r"\b(?:we are hiring|we're hiring|we are looking for|looking for|hiring|"
    r"seeking|candidate for|role at|open position|cerchiamo|stiamo assumendo|"
    r"si cerca|cerca un|cerca una|ricerca|ricercasi|assumiamo|offriamo un|"
    r"posizione aperta|offerta di lavoro)\b",
    re.IGNORECASE)


def _clean_company(candidate):
    """Normalizza un candidato aziendale: taglia punteggiatura finale e frasi."""
    if not candidate:
        return None
    cand = candidate.strip().strip('"\'‘’“”')
    # Taglia alla prima frase o separatore forte.
    cand = re.split(r"[;\n\r]|(?<=[a-z0-9)])\.(?=\s)|,\s|\s+\|\s+", cand, maxsplit=1)[0]
    # Togli articoli iniziali e connettivi finali ("il Gruppo X e" -> "Gruppo X").
    for _ in range(3):
        before = cand
        cand = _LEADING_ARTICLE_RE.sub("", cand).strip()
        cand = _TRAILING_CONNECTOR_RE.sub("", cand).strip()
        if cand == before:
            break
    # Togli la punteggiatura finale, ma conserva le sigle societarie.
    stripped = cand.rstrip(".,;:-–— \t").strip('"\'‘’“”')
    cand = stripped
    if LEGAL_FORM_RE.search(cand):
        cand = cand + "."
    if not cand:
        return None
    words = re.findall(r"[\w&'’.]+", cand)
    if not words or len(words) > 6:
        return None
    if not (2 <= len(cand) <= 40):
        return None
    # Se tutte le parole sono termini di ruolo, non e' un'azienda.
    if all(w.lower() in ROLE_WORDS for w in words):
        return None
    return cand


def _company_from_trigger(text, triggers):
    """Cerca il nome aziendale dopo un trigger ('at', 'presso', ...)."""
    for trigger in triggers:
        for m in re.finditer(r"\b%s\s+" % trigger, text, re.IGNORECASE):
            rest = text[m.end():]
            # Solo la frase corrente.
            chunk = re.split(r"[;\n\r]|(?<=[a-z0-9)])\.(?=\s)", rest, maxsplit=1)[0]
            # Eventuale articolo ("per il Gruppo ...").
            chunk = _LEADING_ARTICLE_RE.sub("", chunk, count=1)
            found = _NAME_RE.match(chunk)
            if not found:
                continue
            cand = _clean_company(found.group(1))
            if cand:
                return cand
    return None


def _company_from_lead(text):
    """Nome aziendale all'inizio della frase: "Acme Corporation is hiring..."."""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Solo la prima riga utile: evita di scambiare una parola qualsiasi
        # ("Si", "We", "Ricerca") per il nome dell'azienda.
        found = _NAME_RE.match(line)
        if found:
            cand = _clean_company(found.group(1))
            if cand and COMPANY_VERB_RE.match(line[found.end():]):
                return cand
        break
    return None


def _company_from_heading(text):
    """Fallback: il nome dell'azienda spesso sta da solo nella prima riga."""
    lines = [l.strip() for l in text.splitlines() if l.strip()][:5]
    for line in lines:
        if not line or len(line) > 40:
            continue
        found = _NAME_RE.match(line)
        if not found:
            continue
        cand = found.group(1).strip()
        rest = line[found.end():].strip()
        # La riga deve essere (quasi) solo il nome aziendale.
        if rest and not CORPORATE_SUFFIX.match(rest):
            continue
        cleaned = _clean_company(cand)
        if cleaned:
            return cleaned
    return None


def extract_company(jd_text):
    """Estrae il nome dell'azienda dall'annuncio."""
    # 1) Etichetta esplicita: "Company: Acme", "Azienda: Initech".
    m = COMPANY_LABEL_RE.search(jd_text)
    if m:
        cand = _clean_company(m.group(1))
        if cand:
            return cand

    # 2) "The client, Swiss Re Global, ..."
    m = CLIENT_LABEL_RE.search(jd_text)
    if m:
        cand = _clean_company(m.group(1))
        if cand:
            return cand

    # 3) Nome in testa alla frase: "Acme Corporation is hiring...".
    cand = _company_from_lead(jd_text)
    if cand:
        return cand

    # 4) Nome isolato in testa all'annuncio ("Banca Intesa Sanpaolo\n...").
    cand = _company_from_heading(jd_text)
    if cand:
        return cand

    # 5) Trigger ("at Acme", "presso Alfa S.p.A.", "About us: Globex").
    for triggers in (EN_TRIGGERS, IT_TRIGGERS):
        cand = _company_from_trigger(jd_text, triggers)
        if cand:
            return cand

    return "Company"


def extract_role(jd_text, lang):
    """Estrae il titolo del ruolo, privilegiando il contesto di assunzione."""
    patterns = ROLE_PATTERNS.get(lang, ROLE_PATTERNS['en'])

    # 1) Etichetta esplicita: "Role: Finance Director", "Posizione: CFO".
    labelled = re.search(
        r"(?:role|position|title|job title|posizione|ruolo|titolo)\s*[:\-–]\s*"
        r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ /&'’()-]{2,50})",
        jd_text, re.IGNORECASE)
    if labelled:
        raw = labelled.group(1).strip(" .,\n\t")
        for pattern, title in patterns:
            if re.search(pattern, raw, re.IGNORECASE):
                return title
        if raw.lower() not in ROLE_WORDS:
            return raw.title()

    # 2/3) Ricerca nel testo, con priorità a: frasi di assunzione, poi
    # prima occorrenza nel documento.
    cues = [m.start() for m in HIRING_CUES.finditer(jd_text)]
    best = None
    for pattern, title in patterns:
        for m in re.finditer(pattern, jd_text, re.IGNORECASE):
            in_cue = any(0 <= (m.start() - cue) <= 60 for cue in cues)
            key = (0 if in_cue else 1, m.start())
            if best is None or key < best[0]:
                best = (key, title)
    if best:
        return best[1]

    # 4) Titolo generico in italiano per l'annuncio italiano.
    return "Finance Director" if lang == 'en' else "Direttore Finanziario"


def extract_info(jd_text, lang):
    company = extract_company(jd_text)
    role = extract_role(jd_text, lang)

    # Key Value: confronto senza diacritici, così "sostenibilita" (annunci
    # scritti senza accenti) viene comunque riconosciuto.
    keywords = (['innovation', 'sustainability', 'growth', 'transformation',
                 'leadership'] if lang == 'en' else
                ['innovazione', 'sostenibilità', 'crescita', 'trasformazione',
                 'eccellenza'])
    haystack = _norm(jd_text)
    char = "mission" if lang == 'en' else "missione"
    for k in keywords:
        if _norm(k) in haystack:
            char = k
            break

    return company, role, char

def create_docs(profile, lang, company, role, char):
    content = profile[lang]
    meta = profile['meta']
    
    # Selezione Temi (MVP: prende i primi 2, in futuro puoi aggiungere logica scoring)
    theme1 = content['capability_themes'][0]
    theme2 = content['capability_themes'][1]
    ev1 = theme1['evidence'][0]
    ev2 = theme2['evidence'][0]
    
    # --- 1. COVER LETTER (Template PDF "Risposta Annuncio Azienda") ---
    doc_cl = Document()
    style = doc_cl.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Intestazione
    doc_cl.add_paragraph(f"{meta['user_id'].replace('_',' ').title()} | {meta['contact_info']['email']} | {meta['contact_info']['phone']}")
    doc_cl.add_paragraph(f"\nSubject: Application for {role} - {company}" if lang == 'en' else f"\nOggetto: Candidatura per {role} - {company}")
    
    if lang == 'en':
        body = f"""
Dear Hiring Team,

I am writing to express my deep interest in the {role} position at {company}.

My admiration for {company} is grounded not only in its leadership role, but also in the company's commitment to {char}. I firmly believe that my professional career reflects these same values, creating a natural alignment between your organization's goals and mine.

In my current role as Strategic Finance Executive, I have developed a deep understanding of {theme1['name']}. My dedication and results, specifically {ev1.lower()}, demonstrate not only my capability in {theme1['keywords'][0]} but also an alignment with the results-oriented approach that {company} embodies.

Furthermore, my experience in {theme2['name']} ({ev2.lower()}) would complement your current team, contributing to guiding the company toward new milestones.

Thank you for considering my application. I am available for an interview to discuss how I can contribute to your success.

Sincerely,

Pierluigi Monaco
"""
    else:
        body = f"""
Gentile Team di Selezione,

Scrivo questa lettera per esprimere il mio profondo interesse per la posizione di {role} presso {company}.

La mia ammirazione per {company} non è solo radicata nel suo ruolo di leader, ma anche nell'impegno dell'azienda verso {char}. Credo fermamente che la mia carriera professionale rifletta questi stessi valori, creando un'armonia naturale tra gli obiettivi della vostra realtà ed i miei.

Nel mio attuale ruolo di Strategic Finance Executive, ho sviluppato una profonda comprensione di {theme1['name']}. Il mio impegno e i risultati ottenuti, specialmente {ev1.lower()}, dimostrano non solo la mia capacità di {theme1['keywords'][0]} ma anche un allineamento con l'approccio orientato al risultato che {company} incarna.

Inoltre, la mia esperienza in {theme2['name']} ({ev2.lower()}) completerebbe il vostro team attuale, contribuendo a guidare l'azienda verso nuovi traguardi.

La ringrazio per aver preso in considerazione la mia candidatura e mi rendo disponibile per un colloquio conoscitivo.

Cordiali Saluti,

Pierluigi Monaco
"""
    doc_cl.add_paragraph(body)
    
    buffer_cl = io.BytesIO()
    doc_cl.save(buffer_cl)
    buffer_cl.seek(0)

    # --- 2. CV OTTIMIZZATO (Formato ATS Lineare) ---
    doc_cv = Document()
    doc_cv.add_heading(meta['user_id'].replace('_',' ').title(), 0)
    doc_cv.add_paragraph(f"{meta['contact_info']['location']} | {meta['contact_info']['phone']} | {meta['contact_info']['email']}")
    
    doc_cv.add_heading('PROFESSIONAL SUMMARY' if lang == 'en' else 'PROFILO PROFESSIONALE', 1)
    doc_cv.add_paragraph(content['summary'])
    
    doc_cv.add_heading('CORE PROJECTS' if lang == 'en' else 'PROGETTI CHIAVE', 1)
    for proj in content['core_projects']:
        p = doc_cv.add_paragraph(style='List Bullet')
        p.add_run(f"{proj['title']} @ {proj['company']}: ").bold = True
        p.add_run(proj['impact'])
        
    doc_cv.add_heading('EXPERIENCE' if lang == 'en' else 'ESPERIENZA', 1)
    # Ruolo 1 (Tailored)
    p = doc_cv.add_paragraph()
    p.add_run("Strategic Finance Executive\n").bold = True
    p.add_run("OpenText / Micro Focus | 2018 - Present")
    doc_cv.add_paragraph(ev1, style='List Bullet') # Evidence mirata 1
    doc_cv.add_paragraph(ev2, style='List Bullet') # Evidence mirata 2
    
    # Ruolo 2 (Statico)
    p = doc_cv.add_paragraph()
    p.add_run("\nFinance Lead\n").bold = True
    p.add_run("Hewlett Packard | 2007 - 2018")
    doc_cv.add_paragraph("Managed P&L for Support & Consulting in EMEA." if lang == 'en' else "Gestione P&L per Support & Consulting in EMEA.", style='List Bullet')
    
    doc_cv.add_heading('SKILLS & EDUCATION' if lang == 'en' else 'COMPETENZE E FORMAZIONE', 1)
    doc_cv.add_paragraph(f"Hard Skills: {', '.join(content['skills']['hard'])}")
    doc_cv.add_paragraph(f"Tools: {', '.join(content['skills']['tools'])}")
    for edu in content['education']:
        doc_cv.add_paragraph(edu, style='List Bullet')

    buffer_cv = io.BytesIO()
    doc_cv.save(buffer_cv)
    buffer_cv.seek(0)
    
    return buffer_cl, buffer_cv

# --- INTERFACCIA STREAMLIT ---
st.title("🚀 Strategic Career Optimizer")
st.markdown("**Pierluigi Monaco** | Executive CV & Cover Letter Generator")
st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 1. Inserisci Annuncio")
    jd_input = st.text_area("Incolla qui la Job Description:", height=300, placeholder="Incolla il testo completo dell'annuncio...")

with col2:
    st.markdown("### 2. Risultati")
    if st.button("✨ Analizza e Genera Documenti", type="primary"):
        if len(jd_input) < 20:
            st.warning("⚠️ Il testo dell'annuncio è troppo breve.")
        else:
            # Carica dati
            profile = yaml.safe_load(PROFILE_YAML)
            
            # Analisi
            lang = detect_language(jd_input)
            company, role, char = extract_info(jd_input, lang)
            
            st.success(f"✅ **Analisi Completata!**")
            st.info(f"🌍 Lingua: **{lang.upper()}**\n🏢 Azienda: **{company}**\n🎯 Ruolo: **{role}**\n🔑 Key Value: **{char}**")
            
            # Generazione
            cl_buffer, cv_buffer = create_docs(profile, lang, company, role, char)
            
            st.markdown("### 📥 Download")
            st.download_button(
                label="📄 Scarica Cover Letter (.docx)",
                data=cl_buffer,
                file_name=f"Cover_Letter_{company}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.download_button(
                label="📄 Scarica CV Ottimizzato (.docx)",
                data=cv_buffer,
                file_name=f"CV_Optimized_{company}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            # Link Contatti
            st.markdown("---")
            st.markdown("### 🕵️ Headhunter Radar")
            q_hr = urllib.parse.quote(f'site:linkedin.com/in/ "{company}" "Talent Acquisition"')
            q_mgr = urllib.parse.quote(f'site:linkedin.com/in/ "{company}" "Finance Director" OR "CFO"')
            
            st.markdown(f"- [🔎 Cerca **HR / Talent Acquisition** su LinkedIn]({f'https://www.google.com/search?q={q_hr}'})")
            st.markdown(f"- [🔎 Cerca **Hiring Manager (CFO)** su LinkedIn]({f'https://www.google.com/search?q={q_mgr}'})")