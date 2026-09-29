"""Hympyr Brand OS — an editable brand system and visual production studio."""
from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import datetime, timezone
from html import escape

import pandas as pd
import streamlit as st
from PIL import Image

from rendering import DEFAULT_LAYERS, color_value, encode_image, font_path, render
from store import Store, client, config, import_legacy, seed

st.set_page_config(page_title="Hympyr Brand OS", page_icon="◆", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
.stApp {background:#f5f8f6;color:#122a1c;font-family:Poppins,sans-serif}
[data-testid="stSidebar"] {background:#073d27} [data-testid="stSidebar"] * {color:#fff}
.block-container {max-width:1440px;padding-top:2rem} h1,h2,h3 {color:#073d27}
.stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"] {background:#1a9e68;border-color:#1a9e68}
</style>""", unsafe_allow_html=True)

CHANNELS = ["Instagram", "LinkedIn", "Facebook", "Carrousel", "Article", "E-mail", "Autre"]
STATUSES = ["Idée", "Brouillon", "À valider", "Validé", "Planifié", "Publié"]
MIMES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
         "svg": "image/svg+xml", "pdf": "application/pdf", "txt": "text/plain", "md": "text/markdown", "html": "text/html"}


def message(error: Exception):
    st.error(f"Opération impossible : {error}")


def auth() -> Store:
    url, key = config()
    if not url or not key:
        st.error("Connexion Supabase à configurer : SUPABASE_URL et SUPABASE_PUBLISHABLE_KEY.")
        st.stop()
    db = client()  # Never share a mutable auth client across Streamlit sessions.
    tokens = st.session_state.get("tokens")
    if tokens:
        try:
            response = db.auth.set_session(tokens["access_token"], tokens["refresh_token"])
            if not response.session or not response.user:
                raise ValueError("Session expirée")
            st.session_state.tokens = {"access_token": response.session.access_token,
                                       "refresh_token": response.session.refresh_token}
            st.session_state.user_email = response.user.email
            return Store(db, str(response.user.id))
        except Exception:
            st.session_state.pop("tokens", None)
    st.title("Accéder au Brand OS")
    mode = st.radio("Compte", ["Connexion", "Créer un compte"], horizontal=True)
    with st.form("auth"):
        email = st.text_input("Adresse e-mail")
        password = st.text_input("Mot de passe", type="password")
        if st.form_submit_button(mode, type="primary"):
            try:
                if mode == "Connexion":
                    response = db.auth.sign_in_with_password({"email": email, "password": password})
                else:
                    response = db.auth.sign_up({"email": email, "password": password})
                if response.session:
                    st.session_state.tokens = {"access_token": response.session.access_token,
                                               "refresh_token": response.session.refresh_token}
                    st.rerun()
                st.success("Vérifiez votre adresse e-mail, puis connectez-vous.")
            except Exception as exc:
                message(exc)
    st.stop()


def brand_data(store: Store):
    colors = store.list("brand_colors", "sort_order", False)
    fonts = store.list("brand_fonts", "family", False)
    assets = store.list("brand_assets")
    templates = store.list("design_templates", "updated_at")
    return colors, fonts, assets, templates


def selector(items: list[dict], label: str, key: str, optional=False) -> str | None:
    choices = ([None] if optional else []) + [item["id"] for item in items]
    labels = {item["id"]: item["name"] for item in items}
    if not choices:
        st.info(f"Créez d'abord un élément dans « {label} ».")
        return None
    return st.selectbox(label, choices, format_func=lambda value: labels.get(value, "Aucun"), key=key)


def dashboard(store: Store, colors, fonts, assets, templates):
    st.title("Hympyr Brand OS")
    st.write("Votre identité de marque, vos gabarits et vos contenus réunis dans un espace de production.")
    contents = store.list("contents", "updated_at")
    cols = st.columns(5)
    for col, title, count in zip(cols, ["Couleurs", "Polices", "Fichiers", "Gabarits", "Contenus"],
                                 [len(colors), len(fonts), len(assets), len(templates), len(contents)]):
        col.metric(title, count)
    st.subheader("Parcours de création")
    st.markdown("**1.** Ajoutez des couleurs, polices et fichiers → **2.** Composez un gabarit à champs → **3.** Rédigez vos diapositives → **4.** Prévisualisez et exportez.")
    st.info("Les couleurs et polices sont reliées aux gabarits par leurs noms. Une modification met à jour les prochains rendus sans toucher aux contenus enregistrés.")
    if contents:
        st.subheader("Derniers contenus")
        st.dataframe(pd.DataFrame([{k: c.get(k) for k in ("title", "channel", "status", "publish_date", "updated_at")}
                                   for c in contents[:10]]), hide_index=True, width="stretch")


def reference_page(store: Store):
    st.title("Référentiel de marque")
    profile = store.list("brand_profiles", "created_at")[0]
    st.caption("Socle initial issu de la charte HYM-CHG-001, version 0.1 du 27 juillet 2026. Validez les formulations avant publication.")
    with st.form("reference"):
        name = st.text_input("Nom", profile["name"])
        descriptor = st.text_input("Activité", profile["descriptor"])
        territory = st.text_input("Territoire", profile["territory"])
        facts = st.text_area("Faits documentés (un par ligne)", "\n".join(profile["facts"]), height=150)
        pending = st.text_area("À valider (un par ligne)", "\n".join(profile["to_validate"]), height=150)
        if st.form_submit_button("Enregistrer", type="primary"):
            store.update("brand_profiles", profile["id"], {"name": name.strip(), "descriptor": descriptor.strip(),
                                                             "territory": territory.strip(),
                                                             "facts": [line.strip() for line in facts.splitlines() if line.strip()],
                                                             "to_validate": [line.strip() for line in pending.splitlines() if line.strip()]})
            st.rerun()
    st.subheader("Vérifications avant diffusion")
    for item in ["Chaque chiffre a une source identifiable et récente.", "La variante du logo correspond au fond.",
                 "Les textes sont lisibles et les droits des visuels sont confirmés.",
                 "Les coordonnées, liens et appels à l'action ont été testés.",
                 "La version finale est validée par une personne identifiée."]:
        st.checkbox(item)


def palette_page(store: Store, colors, fonts):
    st.title("Identité visuelle")
    tab_colors, tab_fonts = st.tabs(["Couleurs", "Google Fonts"])
    with tab_colors:
        st.caption("Les gabarits utilisent les tokens (V-900, O-500…). La suppression d'un token utilisé demande de modifier le gabarit concerné.")
        with st.form("add_color", clear_on_submit=True):
            a, b, c = st.columns(3)
            group = a.text_input("Palette", value="Vert")
            token = b.text_input("Token unique", placeholder="V-950")
            hex_value = c.color_picker("Couleur", "#1A9E68")
            if st.form_submit_button("Ajouter la couleur"):
                try:
                    store.add("brand_colors", {"name": group.strip(), "token": token.strip(), "hex": hex_value.upper(),
                                               "sort_order": len(colors)})
                    st.rerun()
                except Exception as exc:
                    message(exc)
        for color in colors:
            templates = store.list("design_templates", "updated_at")
            used = any(t["background_token"] == color["token"] or
                       any(l.get("color") == color["token"] for l in t["layers"]) for t in templates)
            a, b, c, d = st.columns([1, 2, 1, 1])
            a.color_picker(color["token"], color["hex"], disabled=True, key=f"sw-{color['id']}")
            name = b.text_input("Token", color["token"], key=f"ct-{color['id']}", label_visibility="collapsed")
            value = c.color_picker("HEX", color["hex"], key=f"cv-{color['id']}", label_visibility="collapsed")
            with d:
                if st.button("Enregistrer", key=f"cs-{color['id']}"):
                    try:
                        if used and name.strip() != color["token"]:
                            raise ValueError("Ce token est utilisé dans un gabarit. Modifiez les calques avant de le renommer.")
                        store.update("brand_colors", color["id"], {"token": name.strip(), "hex": value.upper()})
                        st.rerun()
                    except Exception as exc:
                        message(exc)
                if st.button("Supprimer", key=f"cd-{color['id']}"):
                    if used:
                        st.error("Couleur utilisée dans un gabarit. Remplacez son token dans le gabarit avant suppression.")
                    else:
                        store.delete("brand_colors", color["id"])
                        st.rerun()
    with tab_fonts:
        st.write("Indiquez une famille Google Fonts et une graisse. Le rendu PNG télécharge la police à la première utilisation ; si elle est indisponible, un avertissement signale la substitution.")
        with st.form("add_font", clear_on_submit=True):
            a, b = st.columns(2)
            family = a.text_input("Famille", placeholder="Poppins")
            weight = b.selectbox("Graisse", list(range(100, 1000, 100)), index=3)
            if st.form_submit_button("Ajouter la police"):
                if not re.fullmatch(r"[\w -]{1,100}", family.strip()):
                    st.error("Nom de famille invalide.")
                else:
                    try:
                        if not font_path(family.strip(), weight):
                            st.error("Cette variante n'a pas pu être chargée depuis Google Fonts.")
                        else:
                            store.add("brand_fonts", {"family": family.strip(), "weight": weight})
                            st.rerun()
                    except Exception as exc:
                        message(exc)
        for font in fonts:
            templates = store.list("design_templates", "updated_at")
            used = any(l.get("font") == font["family"] and int(l.get("weight") or 700) == font["weight"]
                       for t in templates for l in t["layers"])
            a, b, c = st.columns([3, 1, 1])
            a.write(f"**{escape(font['family'])}** · {font['weight']}")
            if b.button("Modifier", key=f"fe-{font['id']}"):
                st.session_state.edit_font = font["id"]
            if c.button("Supprimer", key=f"fd-{font['id']}"):
                if used:
                    st.error("Police utilisée dans un gabarit. Modifiez les calques avant suppression.")
                else:
                    store.delete("brand_fonts", font["id"])
                    st.rerun()
            if st.session_state.get("edit_font") == font["id"]:
                with st.form(f"font-{font['id']}"):
                    new_family = st.text_input("Famille", font["family"])
                    new_weight = st.selectbox("Graisse", list(range(100, 1000, 100)), index=font["weight"] // 100 - 1)
                    if st.form_submit_button("Enregistrer"):
                        if used and (new_family != font["family"] or new_weight != font["weight"]):
                            st.error("Police utilisée dans un gabarit. Modifiez les calques avant de la renommer.")
                        elif font_path(new_family, new_weight):
                            store.update("brand_fonts", font["id"], {"family": new_family, "weight": new_weight})
                            st.session_state.pop("edit_font", None)
                            st.rerun()
                        else:
                            st.error("Police non disponible.")


def files_page(store: Store, assets):
    st.title("Fichiers de marque")
    st.write("Importez vos logos, images, modèles sources et documents. Un PNG/JPEG/WebP peut servir de fond ou d'élément dans un gabarit.")
    upload, create = st.tabs(["Importer", "Créer un fichier"])
    with upload:
        with st.form("upload", clear_on_submit=True):
            kind = st.selectbox("Type", ["logo", "image", "template", "document"])
            file = st.file_uploader("Fichier", type=list(MIMES))
            if st.form_submit_button("Ajouter", type="primary") and file:
                try:
                    ext = file.name.rsplit(".", 1)[-1].lower()
                    store.upload(file.name, kind, MIMES[ext], file.getvalue())
                    st.rerun()
                except Exception as exc:
                    message(exc)
    with create:
        with st.form("create_text", clear_on_submit=True):
            filename = st.text_input("Nom du fichier", placeholder="brief-campagne.md")
            body = st.text_area("Contenu", height=220)
            if st.form_submit_button("Créer et enregistrer"):
                ext = filename.rsplit(".", 1)[-1].lower()
                if ext not in ("txt", "md", "html"):
                    st.error("Créez un fichier .txt, .md ou .html.")
                else:
                    try:
                        store.upload(filename, "document", MIMES[ext], body.encode("utf-8"))
                        st.rerun()
                    except Exception as exc:
                        message(exc)
    st.subheader("Bibliothèque")
    for asset in assets:
        a, b, c = st.columns([4, 1, 1])
        a.write(f"**{escape(asset['name'])}** · {asset['kind']} · {asset['mime']}")
        try:
            b.download_button("Télécharger", store.download(asset), file_name=asset["name"],
                              mime=asset["mime"], key=f"dl-{asset['id']}")
        except Exception as exc:
            b.warning(str(exc))
        if c.button("Supprimer", key=f"ad-{asset['id']}"):
            try:
                templates = store.list("design_templates", "updated_at")
                if any(t.get("background_asset_id") == asset["id"] or
                       any(l.get("type") == "image" and l.get("field") == asset["id"] for l in t["layers"])
                       for t in templates):
                    raise ValueError("Fichier utilisé dans un gabarit. Retirez-le du gabarit avant suppression.")
                store.remove_asset(asset)
                st.rerun()
            except Exception as exc:
                message(exc)


def asset_loader(store: Store, assets):
    indexed = {asset["id"]: asset for asset in assets}
    cache = {}
    def load(asset_id):
        if asset_id not in indexed:
            raise ValueError("Fichier absent de la bibliothèque.")
        if asset_id not in cache:
            cache[asset_id] = store.download(indexed[asset_id])
        return cache[asset_id]
    return load


def layers_editor(layers: list[dict], key: str) -> list[dict]:
    st.caption("Chaque calque utilise des coordonnées en pixels. Texte : le champ correspond aux saisies du studio ; Image : le champ contient l'ID d'un fichier de la bibliothèque.")
    columns = ["type", "field", "x", "y", "width", "height", "size", "weight", "font", "color", "align"]
    frame = pd.DataFrame([{col: layer.get(col, "" if col in ("field", "font", "color", "align") else 0)
                           for col in columns} for layer in layers], columns=columns)
    edited = st.data_editor(frame, num_rows="dynamic", hide_index=True, width="stretch", key=key,
                            column_config={"type": st.column_config.SelectboxColumn("Type", options=["text", "rect", "image"], required=True),
                                           "align": st.column_config.SelectboxColumn("Alignement", options=["left", "center", "right"])})
    result = []
    for row in edited.fillna("").to_dict("records"):
        if not row["type"]:
            continue
        for col in ("x", "y", "width", "height", "size"):
            row[col] = int(float(row[col] or 0))
        result.append(row)
    return result


def templates_page(store: Store, colors, fonts, assets, templates):
    st.title("Gabarits dynamiques")
    st.write("Créez des formats et placez leurs calques. Les champs texte restent indépendants de la mise en page : les mêmes contenus peuvent être rendus avec un autre gabarit.")
    edit_id = selector(templates, "Modifier un gabarit", "template_select", optional=True)
    selected = next((t for t in templates if t["id"] == edit_id), None)
    prefix = edit_id or "new"
    col1, col2 = st.columns([1, 1])
    with col1:
        name = st.text_input("Nom", value=selected["name"] if selected else "Nouveau gabarit", key=f"tn-{prefix}")
        format_name = st.text_input("Format / usage", value=selected["format"] if selected else "Instagram", key=f"tf-{prefix}")
        a, b = st.columns(2)
        width = a.number_input("Largeur (px)", 200, 4000, int(selected["width"]) if selected else 1080, key=f"tw-{prefix}")
        height = b.number_input("Hauteur (px)", 200, 4000, int(selected["height"]) if selected else 1080, key=f"th-{prefix}")
        tokens = {c["token"]: c["hex"] for c in colors}
        bg_choices = list(tokens) + ["#FFFFFF"]
        current_bg = selected["background_token"] if selected else "V-50"
        background = st.selectbox("Fond", bg_choices, index=bg_choices.index(current_bg) if current_bg in bg_choices else 0,
                                  key=f"tb-{prefix}")
        raster_assets = [a for a in assets if a["mime"] in ("image/png", "image/jpeg", "image/webp")]
        options = [None] + [a["id"] for a in raster_assets]
        current_asset = selected["background_asset_id"] if selected else None
        background_asset = st.selectbox("Image de fond (facultatif)", options,
                                        index=options.index(current_asset) if current_asset in options else 0,
                                        format_func=lambda v: next((a["name"] for a in raster_assets if a["id"] == v), "Aucune"),
                                        key=f"ba-{prefix}")
    with col2:
        st.markdown("**Champs usuels :** `eyebrow`, `title`, `body`, `cta`. Vous pouvez en créer d'autres dans un calque texte.")
        st.markdown("**Calque image :** copiez son ID depuis la liste ci-dessous dans la colonne `field`.")
        for asset in raster_assets:
            st.caption(f"{asset['name']} — `{asset['id']}`")
        st.caption("Pour un modèle conçu ailleurs, importez une image de fond puis superposez les champs éditables.")
    layers = layers_editor(selected["layers"] if selected else DEFAULT_LAYERS, f"layers-{prefix}")
    draft = {"width": width, "height": height, "background_token": background,
             "background_asset_id": background_asset, "layers": layers}
    a, b, c = st.columns(3)
    if a.button("Prévisualiser", key=f"preview-{prefix}"):
        try:
            preview = render(draft, {"eyebrow": "ÉNERGIES EN OCCITANIE", "title": "Votre titre ici",
                                     "body": "Votre texte s'adapte au gabarit.", "cta": "Découvrir"}, tokens,
                             asset_loader(store, assets))
            st.image(preview, width=420)
        except Exception as exc:
            message(exc)
    if b.button("Enregistrer le gabarit", type="primary", key=f"save-{prefix}"):
        try:
            if not name.strip() or not layers:
                raise ValueError("Renseignez un nom et au moins un calque.")
            if any(l["type"] not in ("text", "rect", "image") or l["width"] <= 0 or l["height"] <= 0 for l in layers):
                raise ValueError("Chaque calque doit avoir un type et des dimensions positives.")
            values = {**draft, "name": name.strip(), "format": format_name.strip(),
                      "updated_at": datetime.now(timezone.utc).isoformat()}
            if selected:
                store.update("design_templates", selected["id"], values)
            else:
                store.add("design_templates", values)
            st.rerun()
        except Exception as exc:
            message(exc)
    if selected and c.button("Supprimer le gabarit", key=f"delete-{prefix}"):
        store.delete("design_templates", selected["id"])
        st.rerun()


def _fields(template: dict) -> list[str]:
    return list(dict.fromkeys(str(l.get("field")) for l in template["layers"] if l.get("type") == "text" and l.get("field")))


def _export(images: list[Image.Image], title: str):
    safe = re.sub(r"[^\w-]+", "-", title.lower(), flags=re.UNICODE).strip("-")[:50] or "hympyr"
    if len(images) == 1:
        st.download_button("PNG", encode_image(images[0]), file_name=f"{safe}.png", mime="image/png")
    else:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for number, image in enumerate(images, 1):
                archive.writestr(f"{safe}-{number:02d}.png", encode_image(image))
        st.download_button("PNG (ZIP)", output.getvalue(), file_name=f"{safe}.zip", mime="application/zip")
    output = io.BytesIO()
    images[0].save(output, format="PDF", save_all=True, append_images=images[1:], resolution=96)
    st.download_button("PDF", output.getvalue(), file_name=f"{safe}.pdf", mime="application/pdf")


def studio_page(store: Store, colors, fonts, assets, templates):
    st.title("Studio de contenu")
    st.write("Rédigez le texte, ajoutez des diapositives et choisissez un gabarit. Les faits et chiffres restent sous votre responsabilité éditoriale.")
    if not templates:
        st.info("Créez d'abord un gabarit.")
        return
    existing = store.list("contents", "updated_at")
    if st.session_state.get("pending_content_id"):
        st.session_state.content_select = st.session_state.pop("pending_content_id")
    content_id = selector(existing, "Ouvrir un contenu", "content_select", optional=True)
    content = next((c for c in existing if c["id"] == content_id), None)
    if st.session_state.get("loaded_content") != content_id:
        slides = (store.db.table("slides").select("*").eq("content_id", content_id).eq("owner_id", store.user_id)
                  .order("position").execute().data) if content_id else []
        st.session_state.work_slides = [s["fields"] for s in slides] or [{"title": "", "body": ""}]
        st.session_state.loaded_content = content_id
    template_options = {t["id"]: t for t in templates}
    template_ids = list(template_options)
    current_template = content.get("template_id") if content else None
    selected_template = st.selectbox("Gabarit", template_ids,
                                     index=template_ids.index(current_template) if current_template in template_ids else 0,
                                     format_func=lambda value: template_options[value]["name"])
    template = template_options[selected_template]
    title = st.text_input("Nom du projet", content["title"] if content else "", key=f"project-{content_id}")
    a, b, c = st.columns(3)
    channel = a.selectbox("Canal", CHANNELS, index=CHANNELS.index(content["channel"]) if content and content["channel"] in CHANNELS else 0)
    status = b.selectbox("Statut", STATUSES, index=STATUSES.index(content["status"]) if content and content["status"] in STATUSES else 1)
    publish_date = c.date_input("Publication", value=content.get("publish_date") if content and content.get("publish_date") else None)
    body = st.text_area("Texte de publication", content["body"] if content else "", height=160)
    sources = st.text_area("Sources / validations", content["sources"] if content else "", height=75)
    fields = _fields(template)
    if not fields:
        st.warning("Ce gabarit ne contient aucun champ texte.")
    edited_slides = []
    for index, values in enumerate(st.session_state.work_slides):
        with st.expander(f"Diapositive {index + 1}", expanded=True):
            edited = dict(values)
            for field in fields:
                edited[field] = st.text_area(field, values.get(field, ""), height=90,
                                             key=f"slide-{content_id}-{index}-{field}")
            edited_slides.append(edited)
    st.session_state.work_slides = edited_slides
    a, b, c = st.columns(3)
    if a.button("Ajouter une diapositive", disabled=len(edited_slides) >= 100):
        st.session_state.work_slides.append({})
        st.rerun()
    if b.button("Retirer la dernière", disabled=len(edited_slides) <= 1):
        st.session_state.work_slides.pop()
        st.rerun()
    if c.button("Enregistrer", type="primary"):
        try:
            if not title.strip():
                raise ValueError("Le nom du projet est obligatoire.")
            now = datetime.now(timezone.utc).isoformat()
            values = {"title": title.strip(), "channel": channel, "body": body, "sources": sources,
                      "status": status, "publish_date": publish_date.isoformat() if publish_date else None,
                      "template_id": selected_template, "updated_at": now}
            if content:
                store.update("contents", content["id"], values)
                cid = content["id"]
            else:
                cid = store.add("contents", values)["id"]
            previous = (store.db.table("slides").select("id,position").eq("content_id", cid)
                        .eq("owner_id", store.user_id).order("position").execute().data or [])
            by_position = {int(row["position"]): row["id"] for row in previous}
            for pos, slide in enumerate(edited_slides, 1):
                if pos in by_position:
                    store.update("slides", by_position[pos], {"fields": slide})
                else:
                    store.add("slides", {"content_id": cid, "position": pos, "fields": slide})
            for position, slide_id in by_position.items():
                if position > len(edited_slides):
                    store.delete("slides", slide_id)
            st.session_state.pending_content_id = cid
            st.rerun()
        except Exception as exc:
            message(exc)
    st.subheader("Prévisualisation et exports")
    try:
        tokens = {color["token"]: color["hex"] for color in colors}
        load = asset_loader(store, assets)
        images = [render(template, slide, tokens, load) for slide in edited_slides]
        for i, image in enumerate(images, 1):
            st.image(image, caption=f"Diapositive {i} · {template['width']} × {template['height']} px", width=500)
        for family in {l.get("font") for l in template["layers"] if l.get("type") == "text" and l.get("font")}:
            if not font_path(family, 700):
                st.warning(f"La police {family} est indisponible : l'export utilise DejaVu Sans.")
        _export(images, title)
    except Exception as exc:
        message(exc)
    if content and st.button("Supprimer ce contenu"):
        store.delete("contents", content["id"])
        st.session_state.loaded_content = None
        st.rerun()


def calendar_page(store: Store):
    st.title("Calendrier éditorial")
    contents = store.list("contents", "updated_at")
    if not contents:
        st.info("Aucun contenu pour le moment.")
        return
    st.dataframe(pd.DataFrame([{k: item.get(k) for k in ("title", "channel", "status", "publish_date", "updated_at")}
                               for item in contents]), hide_index=True, width="stretch")
    st.download_button("Exporter en CSV", pd.DataFrame(contents).to_csv(index=False).encode("utf-8-sig"),
                       file_name="calendrier-hympyr.csv", mime="text/csv")


def ideas_page(store: Store):
    st.title("Banque d'idées")
    with st.form("idea", clear_on_submit=True):
        title = st.text_input("Idée")
        a, b = st.columns(2)
        channel = a.selectbox("Canal", CHANNELS)
        priority = b.selectbox("Priorité", ["Basse", "Normale", "Haute", "Urgente"], index=1)
        notes = st.text_area("Notes")
        if st.form_submit_button("Ajouter") and title.strip():
            store.add("ideas", {"title": title.strip(), "channel": channel, "priority": priority,
                                "status": "À explorer", "notes": notes})
            st.rerun()
    ideas = store.list("ideas")
    for idea in ideas:
        a, b = st.columns([5, 1])
        a.write(f"**{escape(idea['title'])}** · {idea['channel']} · {idea['priority']}\n\n{escape(idea['notes'])}")
        if b.button("Supprimer", key=f"idea-{idea['id']}"):
            store.delete("ideas", idea["id"])
            st.rerun()


def settings_page(store: Store):
    st.title("Administration")
    st.write(f"Connecté : **{escape(st.session_state.get('user_email', ''))}**")
    if st.button("Se déconnecter"):
        store.db.auth.sign_out()
        st.session_state.clear()
        st.rerun()
    st.subheader("Sauvegarde JSON")
    payload = {table: store.list(table, "sort_order" if table == "brand_colors" else
                                 "family" if table == "brand_fonts" else
                                 "position" if table == "slides" else
                                 "updated_at" if table in ("contents", "design_templates") else "created_at")
               for table in ("brand_colors", "brand_fonts", "brand_assets", "design_templates", "contents", "slides", "ideas")}
    st.download_button("Exporter les métadonnées", json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name="hympyr-brand-os.json", mime="application/json")
    st.caption("Les fichiers de la bibliothèque se téléchargent individuellement dans l'onglet Fichiers.")
    st.subheader("Importer un export de la V1")
    legacy = st.file_uploader("Fichier hympyr_brand_os_export.json", type="json")
    if legacy and st.button("Importer les contenus et idées"):
        try:
            count_contents, count_ideas = import_legacy(store, json.loads(legacy.getvalue()))
            st.success(f"Importés : {count_contents} contenus et {count_ideas} idées.")
        except Exception as exc:
            message(exc)


def main():
    store = auth()
    try:
        seed(store)
        colors, fonts, assets, templates = brand_data(store)
    except Exception as exc:
        message(exc)
        st.stop()
    st.sidebar.markdown("## ◆ HYMPYR\nÉNERGIES")
    pages = ["Accueil", "Référentiel", "Identité visuelle", "Fichiers", "Gabarits", "Studio", "Calendrier", "Idées", "Administration"]
    page = st.sidebar.radio("Navigation", pages)
    try:
        if page == "Accueil": dashboard(store, colors, fonts, assets, templates)
        elif page == "Référentiel": reference_page(store)
        elif page == "Identité visuelle": palette_page(store, colors, fonts)
        elif page == "Fichiers": files_page(store, assets)
        elif page == "Gabarits": templates_page(store, colors, fonts, assets, templates)
        elif page == "Studio": studio_page(store, colors, fonts, assets, templates)
        elif page == "Calendrier": calendar_page(store)
        elif page == "Idées": ideas_page(store)
        else: settings_page(store)
    except Exception as exc:
        message(exc)


if __name__ == "__main__":
    main()
