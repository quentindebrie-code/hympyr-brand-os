from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import textwrap
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
REFERENCE_DIR = APP_DIR / "reference"
DB_PATH = Path(os.getenv("BRAND_OS_DB", str(DATA_DIR / "brand_os.db")))
CHARTER_PATH = REFERENCE_DIR / "charte_graphique_hympyr.pdf"


BRAND = {
    "name": "Hympyr Energies",
    "descriptor": "Négoce de carburant et vente de granulés de bois",
    "territory": "Occitanie",
    "address": "490 Route de Toulouse, 81370 Saint-Sulpice-la-Pointe",
    "source": "Charte graphique HYM-CHG-001",
    "version": "0.1",
    "status": "Projet",
    "date": "27 juillet 2026",
    "font": "Poppins",
    "brand_facts": [
        "L'activité documentée est le négoce de carburant et la vente de granulés de bois.",
        "La marque revendique un ancrage territorial en Occitanie.",
        "La charte indique une implantation dans son territoire depuis six décennies.",
        "La croix occitane stylisée constitue le symbole territorial de la marque.",
    ],
    "to_validate": [
        "Mission, vision et valeurs formalisées",
        "Promesse commerciale officielle",
        "Audiences prioritaires et personas",
        "Zones et délais de livraison exacts",
        "Chiffres-clés et preuves commerciales",
        "Ton éditorial détaillé",
        "Conversions CMJN et références Pantone",
        "Fichiers vectoriels officiels du logo",
    ],
}


PALETTES = {
    "Vert": [
        ("V-50", "#EAF7F1", "234, 247, 241", "5, 0, 2, 3"),
        ("V-100", "#A8DECE", "168, 222, 206", "24, 0, 7, 13"),
        ("V-300", "#4DC49A", "77, 196, 154", "61, 0, 21, 23"),
        ("V-500", "#1A9E68", "26, 158, 104", "84, 0, 34, 38"),
        ("V-700", "#0F6E46", "15, 110, 70", "86, 0, 36, 57"),
        ("V-900", "#073D27", "7, 61, 39", "89, 0, 36, 76"),
    ],
    "Bleu": [
        ("B-50", "#E6F2FC", "230, 242, 252", "9, 4, 0, 1"),
        ("B-100", "#AACEF2", "170, 206, 242", "30, 15, 0, 5"),
        ("B-400", "#2E78D5", "46, 120, 213", "78, 44, 0, 16"),
        ("B-600", "#1A52A0", "26, 82, 160", "84, 49, 0, 37"),
        ("B-800", "#0F2D52", "15, 45, 82", "82, 45, 0, 68"),
        ("B-950", "#071629", "7, 22, 41", "83, 46, 0, 84"),
    ],
    "Orange": [
        ("O-50", "#FFF0EB", "255, 240, 235", "0, 6, 8, 0"),
        ("O-100", "#FFD0BC", "255, 208, 188", "0, 18, 26, 0"),
        ("O-300", "#FF8C65", "255, 140, 101", "0, 45, 60, 0"),
        ("O-500", "#FF5C28", "255, 92, 40", "0, 64, 84, 0"),
        ("O-700", "#CC3B0F", "204, 59, 15", "0, 71, 93, 20"),
        ("O-900", "#7A2008", "122, 32, 8", "0, 74, 93, 52"),
    ],
}


TEMPLATES = [
    {
        "name": "Publication sociale",
        "category": "Digital",
        "spec": "Format carré · fond V-50 · titre Poppins Bold V-900 · accent orange en pied",
        "status": "Défini dans la charte",
    },
    {
        "name": "Bannière sociale",
        "category": "Digital",
        "spec": "Fond V-900 · logo blanc à gauche · zone droite libre · filet V-500",
        "status": "Défini dans la charte",
    },
    {
        "name": "Présentation 16:9",
        "category": "Bureautique",
        "spec": "33,87 × 19,05 cm · filet V-500 à gauche · fond blanc dominant",
        "status": "Défini dans la charte",
    },
    {
        "name": "Papier à en-tête",
        "category": "Papeterie",
        "spec": "A4 · logo 45 mm · marges 18 mm · bandeau V-900 en pied",
        "status": "Défini dans la charte",
    },
    {
        "name": "Carte de visite",
        "category": "Papeterie",
        "spec": "85 × 55 mm · fond perdu 3 mm · marge de sécurité 4 mm",
        "status": "Défini dans la charte",
    },
    {
        "name": "Signature de courriel",
        "category": "Digital",
        "spec": "Deux colonnes · Arial pour compatibilité · logo 130–150 px",
        "status": "Défini dans la charte",
    },
    {
        "name": "Enseigne de dépôt",
        "category": "Signalétique",
        "spec": "Logo couleur sur blanc ou logo blanc sur V-900 · protection 1 X",
        "status": "Défini dans la charte",
    },
    {
        "name": "Flocage véhicule",
        "category": "Signalétique",
        "spec": "Version couleur ou blanche selon la carrosserie",
        "status": "Principe défini · gabarit à fournir",
    },
]


CONTENT_TYPES = ["LinkedIn", "Facebook", "Instagram", "Carrousel", "Article de blog", "E-mail", "Landing page"]
CONTENT_STATUSES = ["Idée", "À rédiger", "Brouillon", "À valider", "Validé", "Publié"]
PRIORITIES = ["Basse", "Normale", "Haute", "Urgente"]


st.set_page_config(
    page_title="Hympyr Brand OS",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
        :root {
            --v50:#EAF7F1; --v100:#A8DECE; --v500:#1A9E68;
            --v700:#0F6E46; --v900:#073D27; --orange:#FF5C28;
            --blue:#2E78D5; --ink:#10231A; --muted:#607069;
        }
        html, body, [class*="css"], .stApp {font-family:'Poppins',system-ui,sans-serif;}
        .stApp {background:#F7FAF8;color:var(--ink);}
        [data-testid="stSidebar"] {background:var(--v900); border-right:1px solid rgba(255,255,255,.08);}
        [data-testid="stSidebar"] * {color:white;}
        [data-testid="stSidebar"] .stRadio label {padding:.25rem .1rem;}
        [data-testid="stSidebar"] [data-baseweb="radio"] > div:first-child {display:none;}
        [data-testid="stSidebar"] hr {border-color:rgba(255,255,255,.14);}
        .block-container {max-width:1440px;padding-top:2rem;padding-bottom:4rem;}
        h1,h2,h3 {color:var(--v900);letter-spacing:-.025em;}
        h1 {font-size:2.4rem!important;font-weight:700!important;}
        h2 {font-size:1.55rem!important;font-weight:700!important;margin-top:1.6rem!important;}
        h3 {font-size:1.05rem!important;font-weight:600!important;}
        .brand-lockup {padding:1.35rem 1rem 1.1rem;border-bottom:1px solid rgba(255,255,255,.14);margin-bottom:1rem;}
        .brand-lockup .symbol {display:inline-grid;place-items:center;width:40px;height:40px;border-radius:10px;background:var(--v500);font-size:20px;margin-right:10px;vertical-align:middle;}
        .brand-lockup .wordmark {display:inline-block;vertical-align:middle;font-weight:700;letter-spacing:.04em;line-height:1;}
        .brand-lockup small {display:block;margin-top:5px;font-size:.60rem;letter-spacing:.28em;color:var(--v100);}
        .eyebrow {font-size:.72rem;text-transform:uppercase;letter-spacing:.16em;color:var(--v700);font-weight:700;margin-bottom:.4rem;}
        .hero {background:linear-gradient(125deg,var(--v900) 0%,#0B5637 72%,var(--v700) 100%);padding:2.1rem 2.2rem;border-radius:22px;color:white;position:relative;overflow:hidden;margin-bottom:1.3rem;}
        .hero:after {content:"";position:absolute;width:260px;height:260px;border:42px solid rgba(77,196,154,.22);border-radius:50%;right:-90px;top:-135px;}
        .hero h1 {color:white!important;margin:.1rem 0 .55rem!important;font-size:2.25rem!important;}
        .hero p {color:#DDF2E9;margin:0;max-width:760px;line-height:1.6;}
        .pill {display:inline-flex;align-items:center;gap:.4rem;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);padding:.35rem .65rem;border-radius:999px;font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;}
        .dot {width:7px;height:7px;border-radius:50%;background:#FF8C65;display:inline-block;}
        .metric-card,.surface-card {background:white;border:1px solid #DFEAE4;border-radius:16px;padding:1.15rem 1.2rem;height:100%;box-shadow:0 8px 30px rgba(7,61,39,.045);}
        .metric-card .label {font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;font-weight:600;}
        .metric-card .value {font-size:2rem;color:var(--v900);font-weight:700;line-height:1.15;margin:.4rem 0 .2rem;}
        .metric-card .hint {font-size:.74rem;color:var(--muted);}
        .source-note {background:var(--v50);border-left:4px solid var(--v500);padding:.9rem 1rem;border-radius:0 12px 12px 0;color:var(--v900);font-size:.88rem;margin:.7rem 0 1.2rem;}
        .warning-note {background:#FFF0EB;border-left:4px solid var(--orange);padding:.9rem 1rem;border-radius:0 12px 12px 0;color:#5E2411;font-size:.88rem;}
        .color-card {border-radius:14px;overflow:hidden;border:1px solid #DFEAE4;background:white;margin-bottom:.8rem;}
        .color-swatch {height:92px;padding:12px;display:flex;align-items:flex-end;font-weight:700;}
        .color-meta {padding:.7rem .85rem;font-size:.74rem;line-height:1.65;color:#40524A;}
        .spec-tag {display:inline-block;background:var(--v50);color:var(--v700);padding:.25rem .5rem;border-radius:7px;font-size:.7rem;font-weight:600;margin:.15rem .15rem .15rem 0;}
        .template-preview {height:110px;background:var(--v50);border-radius:12px;display:flex;align-items:center;justify-content:center;color:var(--v900);font-weight:700;text-align:center;padding:1rem;border-bottom:6px solid var(--orange);margin-bottom:.8rem;}
        div[data-testid="stForm"] {background:white;border:1px solid #DFEAE4;border-radius:16px;padding:1.1rem 1.15rem;}
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {border-radius:10px;font-weight:600;border-color:var(--v500);}
        .stFormSubmitButton > button[kind="primary"], .stButton > button[kind="primary"] {background:var(--v500);border-color:var(--v500);}
        .stTabs [data-baseweb="tab-list"] {gap:.25rem;background:white;padding:.25rem;border-radius:12px;border:1px solid #DFEAE4;}
        .stTabs [data-baseweb="tab"] {border-radius:9px;}
        .stTabs [aria-selected="true"] {background:var(--v50);color:var(--v900);}
        [data-testid="stDataFrame"] {border:1px solid #DFEAE4;border-radius:12px;overflow:hidden;}
        .footer-note {color:#7A8B82;font-size:.72rem;text-align:center;margin-top:3rem;padding-top:1rem;border-top:1px solid #DFEAE4;}
        @media (max-width: 740px) {.block-container{padding:1rem}.hero{padding:1.4rem}.hero h1{font-size:1.7rem!important;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def ensure_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                channel TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content_type TEXT NOT NULL,
                target TEXT DEFAULT '',
                objective TEXT DEFAULT '',
                body TEXT NOT NULL,
                sources TEXT DEFAULT '',
                status TEXT NOT NULL,
                publish_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )


def query(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(sql, params).fetchall()


def execute(sql: str, params: tuple[Any, ...] = ()) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(sql, params)
        conn.commit()


def page_header(eyebrow: str, title: str, intro: str) -> None:
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.title(title)
    st.write(intro)


def card_metric(label: str, value: str | int, hint: str) -> None:
    st.markdown(
        f'<div class="metric-card"><div class="label">{label}</div><div class="value">{value}</div><div class="hint">{hint}</div></div>',
        unsafe_allow_html=True,
    )


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        raise ValueError("La couleur doit comporter 6 caractères hexadécimaux.")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def relative_luminance(hex_color: str) -> float:
    channels = [value / 255 for value in hex_to_rgb(hex_color)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(color_a: str, color_b: str) -> float:
    lum_a, lum_b = relative_luminance(color_a), relative_luminance(color_b)
    return (max(lum_a, lum_b) + 0.05) / (min(lum_a, lum_b) + 0.05)


def contrast_level(ratio: float) -> str:
    if ratio >= 7:
        return "AAA"
    if ratio >= 4.5:
        return "AA"
    if ratio >= 3:
        return "AA grands textes uniquement"
    return "Non conforme"


def safe_value(value: str, fallback: str = "À compléter") -> str:
    cleaned = " ".join(value.strip().split())
    return cleaned if cleaned else fallback


def build_draft(
    content_type: str,
    subject: str,
    target: str,
    objective: str,
    facts: str,
    cta: str,
    tone: str,
) -> str:
    subject = safe_value(subject)
    target = safe_value(target)
    objective = safe_value(objective)
    cta = safe_value(cta, "[Appel à l'action à définir]")
    facts_lines = [line.strip(" •-\t") for line in facts.splitlines() if line.strip()]
    facts_block = "\n".join(f"- {fact}" for fact in facts_lines) or "- [Ajouter uniquement des faits vérifiés]"
    tone_note = safe_value(tone, "professionnel, clair et humain")

    if content_type == "Carrousel":
        return textwrap.dedent(
            f"""
            CARROUSEL — {subject.upper()}

            Slide 1 — Accroche
            {subject} : l'information essentielle à retenir.

            Slide 2 — Le contexte
            Expliquer le problème rencontré par {target} sans ajouter de chiffre non sourcé.

            Slide 3 — Le premier constat
            Transformer l'un des faits vérifiés ci-dessous en enseignement concret.

            Slide 4 — Le risque à éviter
            Décrire la conséquence opérationnelle avec une formulation prudente.

            Slide 5 — Le bon réflexe
            Présenter une action simple et directement applicable.

            Slide 6 — Le point de vigilance
            Ajouter une limite, une condition ou une précision utile.

            Slide 7 — La méthode
            Décomposer la réponse en trois étapes maximum.

            Slide 8 — La preuve
            Utiliser exclusivement une preuve validée par Hympyr.

            Slide 9 — À retenir
            Résumer le bénéfice principal en une phrase.

            Slide 10 — Action
            {cta}

            FAITS AUTORISÉS POUR LA RÉDACTION
            {facts_block}

            TON
            {tone_note}
            """
        ).strip()

    if content_type == "Article de blog":
        return textwrap.dedent(
            f"""
            TITRE PROVISOIRE
            {subject} : le guide pratique pour {target}

            INTENTION DE RECHERCHE
            {objective}

            META DESCRIPTION
            Découvrez les points essentiels concernant {subject.lower()}, avec une approche claire et opérationnelle proposée par Hympyr Energies.

            INTRODUCTION
            Partir de la situation concrète rencontrée par {target}. Présenter l'enjeu sans dramatisation et annoncer la réponse apportée par l'article.

            H2 — Comprendre {subject.lower()}
            Définition, contexte et vocabulaire utile.

            H2 — Les points essentiels à vérifier
            Organiser les faits validés en sous-parties courtes.

            H2 — Les erreurs à éviter
            Présenter les limites et points de vigilance documentés.

            H2 — Comment Hympyr Energies accompagne ses clients
            Insérer uniquement les services et engagements confirmés.

            FAQ
            Ajouter trois questions réellement posées par les clients.

            CONCLUSION / CTA
            {cta}

            FAITS SOURCÉS DISPONIBLES
            {facts_block}

            TON
            {tone_note}
            """
        ).strip()

    if content_type == "Landing page":
        return textwrap.dedent(
            f"""
            HERO
            H1 : {subject}
            Sous-titre : une réponse claire pour {target}, fondée sur les informations validées par Hympyr Energies.
            CTA principal : {cta}

            PREUVES IMMÉDIATES
            {facts_block}

            SECTION — Votre besoin
            Décrire la situation de {target} et les conséquences concrètes, sans statistique non sourcée.

            SECTION — La réponse Hympyr
            Présenter l'offre, les modalités et la zone couverte uniquement à partir des sources officielles.

            SECTION — Comment cela fonctionne
            1. Prise de contact
            2. Qualification du besoin
            3. Proposition adaptée

            SECTION — FAQ
            Ajouter les objections et questions réellement remontées par les équipes.

            CTA FINAL
            {cta}

            OBJECTIF DE CONVERSION
            {objective}

            TON
            {tone_note}
            """
        ).strip()

    if content_type == "E-mail":
        return textwrap.dedent(
            f"""
            OBJET : {subject} — l'essentiel à retenir
            PRÉ-EN-TÊTE : Une information utile pour {target}.

            Bonjour [Prénom],

            Vous êtes peut-être concerné par {subject.lower()}.

            [Reformuler ici le problème concret en une phrase, sans extrapolation.]

            Ce qu'il faut retenir :
            {facts_block}

            {cta}

            L'équipe Hympyr Energies

            TON : {tone_note}
            OBJECTIF : {objective}
            """
        ).strip()

    platform_hint = "publication professionnelle" if content_type == "LinkedIn" else "publication sociale"
    return textwrap.dedent(
        f"""
        ACCROCHE
        {subject} : ce que {target} doit savoir.

        TEXTE
        Rédiger une {platform_hint} qui part d'une situation réelle, explique l'enjeu simplement et utilise uniquement les informations suivantes :

        {facts_block}

        CONCLUSION
        Relier ces informations à l'objectif « {objective} » sans ajouter de promesse non vérifiée.

        APPEL À L'ACTION
        {cta}

        TON
        {tone_note}

        HASHTAGS À VALIDER
        #HympyrEnergies #Occitanie
        """
    ).strip()


def export_database() -> bytes:
    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "brand": BRAND,
        "ideas": [dict(row) for row in query("SELECT * FROM ideas ORDER BY id")],
        "contents": [dict(row) for row in query("SELECT * FROM contents ORDER BY id")],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def require_optional_password() -> None:
    try:
        expected = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        expected = ""
    if not expected:
        return
    if st.session_state.get("authenticated"):
        return
    st.markdown("## Accès au Brand OS")
    submitted = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter", type="primary"):
        if submitted == expected:
            st.session_state.authenticated = True
            st.rerun()
        st.error("Mot de passe incorrect.")
    st.stop()


def sidebar() -> str:
    st.sidebar.markdown(
        """
        <div class="brand-lockup">
          <span class="symbol">✦</span><span class="wordmark">HYMPYR<small>ÉNERGIES</small></span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pages = [
        "Vue d'ensemble",
        "ADN de marque",
        "Charte interactive",
        "Gabarits",
        "Studio de contenu",
        "Calendrier éditorial",
        "Banque d'idées",
        "Conformité",
        "Administration",
    ]
    page = st.sidebar.radio("Navigation", pages, label_visibility="collapsed")
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Charte {BRAND['version']} · {BRAND['status']}")
    st.sidebar.caption("Source : HYM-CHG-001")
    return page


def dashboard_page() -> None:
    contents = query("SELECT status, COUNT(*) AS count FROM contents GROUP BY status")
    ideas_count = query("SELECT COUNT(*) AS count FROM ideas")[0]["count"]
    content_count = sum(row["count"] for row in contents)
    validated = sum(row["count"] for row in contents if row["status"] in {"Validé", "Publié"})
    planned = query("SELECT COUNT(*) AS count FROM contents WHERE publish_date IS NOT NULL AND publish_date != ''")[0]["count"]

    st.markdown(
        """
        <div class="hero">
          <span class="pill"><span class="dot"></span> Socle de marque centralisé</span>
          <h1>Le Brand OS de Hympyr Energies</h1>
          <p>Une source unique pour consulter la charte, préparer les contenus, organiser les campagnes et sécuriser chaque prise de parole.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(4)
    with cols[0]:
        card_metric("Contenus", content_count, "Tous statuts confondus")
    with cols[1]:
        card_metric("Validés / publiés", validated, "Prêts à être réutilisés")
    with cols[2]:
        card_metric("Planifiés", planned, "Avec une date de publication")
    with cols[3]:
        card_metric("Idées", ideas_count, "Dans le backlog éditorial")

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.subheader("Fondations disponibles")
        st.markdown(
            """
            <div class="surface-card">
              <span class="spec-tag">Logo</span><span class="spec-tag">18 couleurs</span><span class="spec-tag">Poppins</span><span class="spec-tag">WCAG</span><span class="spec-tag">8 applications</span>
              <p style="margin-top:1rem;color:#40524A;line-height:1.7">La charte HYM-CHG-001 constitue le socle de cette version. Ses informations validées sont intégrées directement dans l'application ; aucun fichier YAML externe n'est requis.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.subheader("Derniers contenus")
        recent = query("SELECT title, content_type, status, publish_date FROM contents ORDER BY updated_at DESC LIMIT 6")
        if recent:
            st.dataframe(pd.DataFrame([dict(row) for row in recent]), width="stretch", hide_index=True)
        else:
            st.info("Aucun contenu enregistré. Le Studio de contenu permet de créer le premier brouillon.")
    with right:
        st.subheader("Points à compléter")
        for item in BRAND["to_validate"][:6]:
            st.markdown(f"- {item}")
        st.markdown(
            '<div class="warning-note"><strong>Règle de fiabilité</strong><br>Une information absente de la charte n’est jamais présentée comme acquise. Elle reste marquée « à valider ».</div>',
            unsafe_allow_html=True,
        )


def brand_page() -> None:
    page_header("Fondations", "ADN de marque", "Les informations ci-dessous proviennent directement de la charte graphique fournie.")
    st.markdown('<div class="source-note"><strong>Source primaire :</strong> HYM-CHG-001 · version 0.1 · statut Projet · 27 juillet 2026.</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a:
        st.markdown('<div class="surface-card"><div class="eyebrow">Activité</div><h3>Négoce de carburant et vente de granulés de bois</h3><p>Formulation issue de la signature du logo.</p></div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="surface-card"><div class="eyebrow">Territoire</div><h3>Occitanie</h3><p>Ancrage porté par la croix occitane stylisée.</p></div>', unsafe_allow_html=True)
    with c:
        st.markdown('<div class="surface-card"><div class="eyebrow">Identité</div><h3>Hympyr Energies</h3><p>Marque structurée autour du vert, avec bleu fonctionnel et orange d’accent.</p></div>', unsafe_allow_html=True)

    st.subheader("Faits documentés")
    for fact in BRAND["brand_facts"]:
        st.success(fact, icon="✅")

    st.subheader("Plateforme de marque à formaliser")
    frame = pd.DataFrame({"Élément": BRAND["to_validate"], "Statut": ["À valider"] * len(BRAND["to_validate"])})
    st.dataframe(frame, width="stretch", hide_index=True)


def render_palette(name: str, colors: list[tuple[str, str, str, str]]) -> None:
    st.markdown(f"### Palette {name.lower()}")
    cols = st.columns(3)
    for index, (token, hex_code, rgb, cmyk) in enumerate(colors):
        text_color = "#FFFFFF" if contrast_ratio(hex_code, "#FFFFFF") >= contrast_ratio(hex_code, "#073D27") else "#073D27"
        with cols[index % 3]:
            st.markdown(
                f'<div class="color-card"><div class="color-swatch" style="background:{hex_code};color:{text_color}">{token} · {hex_code}</div><div class="color-meta">RVB&nbsp; {rgb}<br>CMJN&nbsp; {cmyk}</div></div>',
                unsafe_allow_html=True,
            )


def charter_page() -> None:
    page_header("Système visuel", "Charte interactive", "Consultez les règles, copiez les références et vérifiez les contrastes avant production.")
    logo_tab, colors_tab, typo_tab, contrast_tab = st.tabs(["Logo", "Couleurs", "Typographie", "Contrastes"])

    with logo_tab:
        st.markdown('<div class="warning-note"><strong>Fichiers officiels manquants :</strong> la charte précise que seuls les SVG, PDF ou EPS originaux font foi. Aucun logo n’est recréé ni proposé au téléchargement dans cette V1.</div>', unsafe_allow_html=True)
        st.subheader("Composition")
        c1, c2, c3 = st.columns(3)
        for col, title, body in [
            (c1, "Symbole", "Croix occitane stylisée réservée en blanc dans un cartouche vert à angles arrondis."),
            (c2, "Logotype", "« HYMPYR » et « ÉNERGIES » en capitales, avec proportions et agencement fixes."),
            (c3, "Signature", "Descriptif d’activité associé au logo complet."),
        ]:
            with col:
                st.markdown(f'<div class="surface-card"><div class="eyebrow">Élément</div><h3>{title}</h3><p>{body}</p></div>', unsafe_allow_html=True)

        st.subheader("Règles essentielles")
        rules = pd.DataFrame(
            [
                ["Zone de protection", "1/2 X sur chaque côté ; 1 X sur enseigne"],
                ["Taille minimale impression", "Logo complet 28 mm · symbole 10 mm"],
                ["Taille minimale écran", "Logo complet 150 px · symbole 48 px"],
                ["Fond clair", "Version principale quadrichromie"],
                ["Fond foncé ou vert", "Version monochrome blanche"],
                ["Photographie", "Version blanche sur une zone sombre et peu chargée"],
            ],
            columns=["Situation", "Règle"],
        )
        st.dataframe(rules, width="stretch", hide_index=True)
        st.subheader("Interdits")
        st.write("Déformer · incliner · changer les couleurs · recomposer · ajouter des effets · poser sur un fond chargé · changer la police · réduire sous le minimum · recréer le logo.")

    with colors_tab:
        st.markdown("**Répartition recommandée :** environ 60 % de base, 30 % de structure et 10 % d’accent.")
        st.info("Les valeurs HEX et RVB sont les références exactes. Les conversions CMJN restent indicatives et doivent être validées avec l’imprimeur.")
        for palette_name, palette in PALETTES.items():
            render_palette(palette_name, palette)

    with typo_tab:
        st.markdown("## Poppins")
        st.write("Police unique, géométrique et sans empattement. Licence SIL Open Font Licence 1.1.")
        typo = pd.DataFrame(
            [
                ["Display", "Bold", "40 px / 24 pt", "Capitales pour les grands titres"],
                ["Titre 1", "Semibold", "32 px / 24 pt", "Titre principal"],
                ["Titre 2", "Semibold", "24 px / 18 pt", "Titre de section"],
                ["Titre 3", "Medium", "18 px / 13 pt", "Sous-section"],
                ["Corps", "Regular", "12 px / 10,5 pt", "Paragraphes courants"],
                ["Légende", "Regular", "10 px / 8 pt", "Notes et mentions"],
            ],
            columns=["Niveau", "Graisse", "Numérique / impression", "Usage"],
        )
        st.dataframe(typo, width="stretch", hide_index=True)
        st.caption("La page des graisses de la charte comporte des libellés répétés. Cette table reprend les usages cohérents avec l’échelle typographique explicitement documentée.")

    with contrast_tab:
        st.subheader("Contrôleur WCAG")
        col1, col2 = st.columns(2)
        with col1:
            foreground = st.color_picker("Couleur du texte", "#073D27")
        with col2:
            background = st.color_picker("Couleur du fond", "#FFFFFF")
        ratio = contrast_ratio(foreground, background)
        level = contrast_level(ratio)
        st.markdown(
            f'<div class="surface-card" style="background:{background};color:{foreground};min-height:150px"><div style="font-size:1.55rem;font-weight:700">Aperçu Hympyr Energies</div><p>Un texte lisible, cohérent et accessible sur tous les supports.</p></div>',
            unsafe_allow_html=True,
        )
        a, b = st.columns(2)
        with a:
            st.metric("Ratio de contraste", f"{ratio:.2f}:1")
        with b:
            st.metric("Niveau", level)
        if ratio >= 4.5:
            st.success("Cette combinaison convient au texte courant selon WCAG 2.1 AA.")
        elif ratio >= 3:
            st.warning("À réserver aux grands textes : 24 px minimum, ou 19 px en gras.")
        else:
            st.error("Contraste insuffisant. Choisissez une autre combinaison.")


def templates_page() -> None:
    page_header("Bibliothèque", "Gabarits de marque", "Les applications décrites dans la charte sont regroupées ici avec leurs règles de production.")
    category = st.selectbox("Filtrer par catégorie", ["Toutes"] + sorted({item["category"] for item in TEMPLATES}))
    selected = TEMPLATES if category == "Toutes" else [item for item in TEMPLATES if item["category"] == category]
    for start in range(0, len(selected), 3):
        cols = st.columns(3)
        for col, item in zip(cols, selected[start : start + 3]):
            with col:
                st.markdown(
                    f'<div class="surface-card"><div class="template-preview">{item["name"]}</div><span class="spec-tag">{item["category"]}</span><h3>{item["name"]}</h3><p>{item["spec"]}</p><small>{item["status"]}</small></div>',
                    unsafe_allow_html=True,
                )
    st.markdown("### Disponibilité des fichiers")
    st.warning("Les modèles éditables et fichiers vectoriels n’ont pas été fournis. Cette V1 documente donc les règles sans prétendre distribuer des fichiers sources officiels.")


def studio_page() -> None:
    page_header("Création", "Studio de contenu", "Créez une trame conforme en utilisant uniquement les faits que vous renseignez et pouvez vérifier.")
    st.markdown('<div class="source-note"><strong>Principe :</strong> le studio structure un brouillon, mais n’invente ni chiffre, ni délai, ni zone de livraison, ni promesse commerciale.</div>', unsafe_allow_html=True)

    with st.form("content_studio"):
        col1, col2 = st.columns(2)
        with col1:
            content_type = st.selectbox("Format", CONTENT_TYPES)
            subject = st.text_input("Sujet *", placeholder="Ex. préparer sa cuve avant une livraison")
            target = st.text_input("Public", placeholder="Ex. responsables de chantier")
        with col2:
            objective = st.text_input("Objectif", placeholder="Ex. faciliter la prise de contact")
            cta = st.text_input("Appel à l’action", placeholder="Ex. Demandez votre devis")
            tone = st.text_input("Ton", value="Professionnel, clair, concret et rassurant")
        facts = st.text_area("Faits vérifiés — un par ligne", height=130, placeholder="Chaque ligne doit pouvoir être reliée à une source interne ou publique fiable.")
        sources = st.text_area("Sources et références", height=80, placeholder="URL, document, personne ayant validé, date…")
        submitted = st.form_submit_button("Générer la trame", type="primary", width="stretch")

    if submitted:
        if not subject.strip():
            st.error("Le sujet est obligatoire.")
        else:
            st.session_state.generated_draft = build_draft(content_type, subject, target, objective, facts, cta, tone)
            st.session_state.generated_meta = {
                "title": subject.strip(),
                "content_type": content_type,
                "target": target.strip(),
                "objective": objective.strip(),
                "sources": sources.strip(),
            }

    if st.session_state.get("generated_draft"):
        st.subheader("Brouillon structuré")
        edited = st.text_area("Contenu", value=st.session_state.generated_draft, height=520, key="draft_editor")
        st.download_button("Télécharger en texte", edited.encode("utf-8"), file_name="brouillon_hympyr.txt", mime="text/plain")
        save_col, date_col = st.columns([1, 1])
        with save_col:
            status = st.selectbox("Statut à l’enregistrement", CONTENT_STATUSES, index=2)
        with date_col:
            plan_date = st.date_input("Date envisagée", value=None)
        if st.button("Enregistrer dans le Brand OS", type="primary"):
            meta = st.session_state.generated_meta
            now = datetime.now().isoformat(timespec="seconds")
            execute(
                "INSERT INTO contents (title, content_type, target, objective, body, sources, status, publish_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    meta["title"], meta["content_type"], meta["target"], meta["objective"], edited,
                    meta["sources"], status, plan_date.isoformat() if plan_date else "", now, now,
                ),
            )
            st.success("Le contenu a été enregistré.")


def calendar_page() -> None:
    page_header("Organisation", "Calendrier éditorial", "Centralisez les brouillons, leurs statuts et les dates envisagées.")
    rows = query("SELECT id, publish_date, title, content_type, target, status, updated_at FROM contents ORDER BY CASE WHEN publish_date = '' THEN 1 ELSE 0 END, publish_date, updated_at DESC")
    if not rows:
        st.info("Aucun contenu enregistré pour le moment.")
        return
    frame = pd.DataFrame([dict(row) for row in rows])
    frame.columns = ["ID", "Date", "Titre", "Format", "Public", "Statut", "Mis à jour"]
    selected_status = st.multiselect("Statuts", CONTENT_STATUSES, default=CONTENT_STATUSES)
    filtered = frame[frame["Statut"].isin(selected_status)]
    st.dataframe(filtered, width="stretch", hide_index=True)
    csv_buffer = io.StringIO()
    filtered.to_csv(csv_buffer, index=False, quoting=csv.QUOTE_MINIMAL)
    st.download_button("Exporter la vue en CSV", csv_buffer.getvalue().encode("utf-8-sig"), "calendrier_editorial_hympyr.csv", "text/csv")

    st.subheader("Mettre à jour un contenu")
    ids = [int(row["id"]) for row in rows]
    content_id = st.selectbox("Contenu", ids, format_func=lambda value: next(row["title"] for row in rows if row["id"] == value))
    selected_row = next(row for row in rows if row["id"] == content_id)
    col1, col2 = st.columns(2)
    with col1:
        current_index = CONTENT_STATUSES.index(selected_row["status"]) if selected_row["status"] in CONTENT_STATUSES else 0
        new_status = st.selectbox("Nouveau statut", CONTENT_STATUSES, index=current_index)
    with col2:
        existing_date = date.fromisoformat(selected_row["publish_date"]) if selected_row["publish_date"] else None
        new_date = st.date_input("Date de publication", value=existing_date)
    if st.button("Mettre à jour"):
        execute(
            "UPDATE contents SET status = ?, publish_date = ?, updated_at = ? WHERE id = ?",
            (new_status, new_date.isoformat() if new_date else "", datetime.now().isoformat(timespec="seconds"), content_id),
        )
        st.success("Contenu mis à jour.")
        st.rerun()


def ideas_page() -> None:
    page_header("Backlog", "Banque d’idées", "Capturez les sujets à explorer avant de les transformer en contenus.")
    with st.form("idea_form", clear_on_submit=True):
        title = st.text_input("Idée *", placeholder="Ex. FAQ sur la livraison de GNR")
        a, b, c = st.columns(3)
        with a:
            channel = st.selectbox("Canal", CONTENT_TYPES)
        with b:
            priority = st.selectbox("Priorité", PRIORITIES, index=1)
        with c:
            status = st.selectbox("Statut", ["À explorer", "Retenue", "En production", "Écartée"])
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Ajouter l’idée", type="primary")
        if submitted:
            if not title.strip():
                st.error("Le titre est obligatoire.")
            else:
                execute(
                    "INSERT INTO ideas (title, channel, priority, status, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (title.strip(), channel, priority, status, notes.strip(), datetime.now().isoformat(timespec="seconds")),
                )
                st.success("Idée ajoutée.")

    rows = query("SELECT id, title, channel, priority, status, notes, created_at FROM ideas ORDER BY id DESC")
    if rows:
        st.dataframe(pd.DataFrame([dict(row) for row in rows]), width="stretch", hide_index=True)
        with st.expander("Supprimer une idée"):
            idea_id = st.selectbox("Idée à supprimer", [int(row["id"]) for row in rows], format_func=lambda value: next(row["title"] for row in rows if row["id"] == value))
            confirm = st.checkbox("Je confirme la suppression définitive de cette idée")
            if st.button("Supprimer", disabled=not confirm):
                execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
                st.success("Idée supprimée.")
                st.rerun()
    else:
        st.info("La banque d’idées est vide.")


def compliance_page() -> None:
    page_header("Contrôle qualité", "Conformité", "Une grille de vérification avant toute validation ou publication.")
    sections = {
        "Fiabilité du contenu": [
            "Chaque chiffre est relié à une source identifiable et récente.",
            "Les délais, territoires et conditions commerciales sont validés en interne.",
            "Aucune donnée provisoire n'est présentée comme définitive.",
            "Les termes techniques ont été relus par une personne compétente.",
        ],
        "Identité visuelle": [
            "La variante du logo correspond au fond utilisé.",
            "La zone de protection et la taille minimale sont respectées.",
            "L'orange reste un accent ponctuel.",
            "Poppins est utilisée, sauf contrainte technique documentée.",
        ],
        "Accessibilité et diffusion": [
            "Le contraste atteint au moins 4,5:1 pour le texte courant.",
            "Les images importantes disposent d'un texte alternatif.",
            "Le contenu est compréhensible sans dépendre uniquement de la couleur.",
            "Le support a été vérifié sur ordinateur et mobile.",
        ],
        "Validation humaine": [
            "Une personne identifiée assume la validation finale.",
            "Les coordonnées, liens et appels à l'action ont été testés.",
            "Les droits d'utilisation des visuels sont confirmés.",
            "La version finale est archivée avec sa date et ses sources.",
        ],
    }
    total = sum(len(items) for items in sections.values())
    checked = 0
    for section, items in sections.items():
        st.subheader(section)
        for index, item in enumerate(items):
            if st.checkbox(item, key=f"compliance_{section}_{index}"):
                checked += 1
    ratio = checked / total
    st.progress(ratio)
    st.write(f"**{checked}/{total} contrôles effectués**")
    if checked == total:
        st.success("Tous les contrôles de cette grille sont cochés. La validation finale reste humaine.")


def admin_page() -> None:
    page_header("Paramètres", "Administration", "Sauvegardes, document source et informations techniques de la V1.")
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Sauvegarde")
        st.write("Téléchargez régulièrement une copie des contenus et idées. Le fichier inclut également le référentiel de marque embarqué.")
        st.download_button("Exporter toutes les données", export_database(), "hympyr_brand_os_export.json", "application/json", type="primary")
        st.caption("Sur Streamlit Community Cloud, le stockage local peut être réinitialisé lors d’un redéploiement.")
    with right:
        st.subheader("Charte source")
        if CHARTER_PATH.exists():
            st.write("Charte graphique HYM-CHG-001 · version 0.1 · Projet")
            st.download_button("Télécharger la charte PDF", CHARTER_PATH.read_bytes(), CHARTER_PATH.name, "application/pdf")
        else:
            st.warning("Le PDF de référence n’est pas présent dans le dossier `reference`. L’application reste fonctionnelle car les données essentielles sont embarquées.")

    st.subheader("État du référentiel")
    status = pd.DataFrame(
        [
            ["Charte graphique", "Disponible", "HYM-CHG-001 v0.1"],
            ["Palette numérique", "Intégrée", "18 couleurs HEX et RVB"],
            ["Accessibilité", "Intégrée", "Contrôleur WCAG"],
            ["Logos vectoriels", "Manquants", "À fournir en SVG/PDF/EPS"],
            ["Plateforme de marque", "Partielle", "Mission, vision, valeurs à valider"],
            ["Base de données", "Locale", str(DB_PATH.name)],
        ],
        columns=["Élément", "État", "Détail"],
    )
    st.dataframe(status, width="stretch", hide_index=True)

    st.subheader("Déploiement")
    st.code(
        """# Streamlit Community Cloud
Main file path: app.py

# Lancement local
pip install -r requirements.txt
streamlit run app.py""",
        language="bash",
    )
    st.info("Protection facultative : ajoutez `APP_PASSWORD` dans les secrets Streamlit. Ne placez jamais de mot de passe ou de clé API directement dans le dépôt.")


def main() -> None:
    inject_css()
    ensure_db()
    require_optional_password()
    page = sidebar()
    routes = {
        "Vue d'ensemble": dashboard_page,
        "ADN de marque": brand_page,
        "Charte interactive": charter_page,
        "Gabarits": templates_page,
        "Studio de contenu": studio_page,
        "Calendrier éditorial": calendar_page,
        "Banque d'idées": ideas_page,
        "Conformité": compliance_page,
        "Administration": admin_page,
    }
    routes[page]()
    st.markdown('<div class="footer-note">Hympyr Brand OS · Référentiel HYM-CHG-001 · Une information non validée reste explicitement provisoire.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
