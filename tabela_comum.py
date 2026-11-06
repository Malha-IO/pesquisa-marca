"""Partes comuns: lista de candidatos, estado dos processos e a tabela (MD e CSV)."""
import csv
import json
import os
import re
import unicodedata
from datetime import datetime

DIR = os.path.dirname(os.path.abspath(__file__))
CSV_IN = os.path.join(DIR, "candidatos.csv")
RES_INPI = os.path.join(DIR, "resultados.json")
RES_PRES = os.path.join(DIR, "presenca.json")
STATUS = os.path.join(DIR, "status.json")
TAB_MD = os.path.join(DIR, "tabela.md")
TAB_CSV = os.path.join(DIR, "tabela.csv")

DOMAINS = ("com", "io", "ai", "com.br")


def handle(nome):
    s = unicodedata.normalize("NFD", nome)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def load_csv():
    with open(CSV_IN, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("nome") or "").strip()]
    for r in rows:
        for k in ("origem", "leva", "ideia", "nota"):
            r[k] = (r.get(k) or "").strip()
        r["nome"] = r["nome"].strip()
        try:
            r["prioridade"] = int(r.get("prioridade") or 3)
        except ValueError:
            r["prioridade"] = 3
    return rows


def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def set_status(key, text):
    st = load_json(STATUS)
    st[key] = text
    save_json(STATUS, st)


# ---------- células ----------

def inpi_cell(c):
    parts = []
    if c["exata_ativas_ncl"]:
        parts.append(f"tomado: {c['exata_ativas_ncl'][0]['titular'][:40]}")
    if c["exata_ativas_antigas"]:
        parts.append(f"{len(c['exata_ativas_antigas'])} antiga(s) em vigor")
    if c["radical_ativas"]:
        parts.append(f"{len(c['radical_ativas'])} parecida(s)")
    return "; ".join(parts) or "livre"


def similares(cls):
    names = []
    for k in ("9", "42"):
        for r in cls[k]["radical_ativas"]:
            names.append(f"{r['marca'][:30]} ({k})")
    names = list(dict.fromkeys(names))
    if not names:
        return ""
    return ", ".join(names[:3]) + (f" +{len(names) - 3}" if len(names) > 3 else "")


def manual_links(h):
    return {
        "Instagram": f"https://www.instagram.com/{h}/",
        "TikTok": f"https://www.tiktok.com/@{h}",
        "Facebook": f"https://www.facebook.com/{h}",
        "LinkedIn": f"https://www.linkedin.com/company/{h}",
    }


def write_table():
    cands = load_csv()
    inpi = load_json(RES_INPI)
    pres = load_json(RES_PRES)
    st = load_json(STATUS)
    order = {"limpo": 0, "ressalva": 1, "pendente": 2, "tomado": 3}

    rows = []
    for c in cands:
        r = inpi.get(c["nome"])
        v = r["veredito"] if r else "pendente"
        rows.append((order[v], c["prioridade"], c["nome"], c, r, v, pres.get(c["nome"])))
    rows.sort(key=lambda x: (x[0], x[1], x[2]))

    md = [
        "# Candidatos a marca do produto",
        "",
        f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}.",
        "",
        f"- **INPI:** {st.get('inpi', 'não iniciado')}",
        f"- **Domínios e redes:** {st.get('presenca', 'não iniciado')}",
        "",
        "**INPI:** limpo = nada ativo nas classes 9 e 42; ressalva = marca parecida ativa ou registro antigo em vigor; "
        "tomado = mesma marca ativa. Busca limpa não garante registro: falta a análise fonética.",
        "",
        "**Domínios:** livre? = sem DNS e sem registro na consulta pública (confirmar no registrador); "
        "à venda = estacionado em plataforma de revenda. **GitHub e X:** verificação automática. "
        "**Instagram, TikTok, Facebook e LinkedIn** não respondem sem login: use os links do arquivo tabela.csv.",
        "",
        "| Nome | @ | Origem | Ideia | INPI | Classe 9 | Classe 42 | Parecidas | .com | .io | .ai | .com.br | GitHub | X | Nota |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    out_csv = []
    for _, _, _, c, r, v, p in rows:
        h = handle(c["nome"])
        c9 = inpi_cell(r["classes"]["9"]) if r else "…"
        c42 = inpi_cell(r["classes"]["42"]) if r else "…"
        sim = similares(r["classes"]) if r else ""
        dom = {d: (p or {}).get("dominios", {}).get(d, "…") for d in DOMAINS}
        gh = (p or {}).get("github", "…")
        xx = (p or {}).get("x", "…")
        md.append(f"| **{c['nome']}** | {h} | {c['origem']} | {c['ideia']} | {v} | {c9} | {c42} | {sim} | "
                  f"{dom['com']} | {dom['io']} | {dom['ai']} | {dom['com.br']} | {gh} | {xx} | {c.get('nota', '')} |")
        links = manual_links(h)
        out_csv.append({
            "nome": c["nome"], "handle": h, "origem": c["origem"], "leva": c.get("leva", ""),
            "prioridade": c["prioridade"], "ideia": c["ideia"], "inpi": v,
            "classe_9": c9, "classe_42": c42, "parecidas": sim,
            ".com": dom["com"], ".io": dom["io"], ".ai": dom["ai"], ".com.br": dom["com.br"],
            "github": gh, "x": xx,
            "instagram_checar": links["Instagram"], "tiktok_checar": links["TikTok"],
            "facebook_checar": links["Facebook"], "linkedin_checar": links["LinkedIn"],
            "nota": c.get("nota", ""),
        })

    tmp = TAB_MD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    os.replace(tmp, TAB_MD)

    tmp = TAB_CSV + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_csv[0].keys()) if out_csv else ["nome"])
        w.writeheader()
        w.writerows(out_csv)
    os.replace(tmp, TAB_CSV)
