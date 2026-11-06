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


# Sufixos que só descrevem o produto. O INPI tende a ignorá-los e comparar o resto (o núcleo).
# Maiúsculas importam: "NimboOS" tem núcleo "Nimbo", mas "Cosmos" não tem sufixo.
SUFIXOS = ("OS", "AI", "IO", "HQ", "App", "Apps", "Hub", "Lab", "Labs", "Cloud", "Tech", "Soft", "Bot", "Flow", "Ops")
CONFIG = os.path.join(DIR, "config.json")
ORDEM = {"limpo": 0, "ressalva": 1, "risco": 2, "pendente": 3, "tomado": 4}


def nucleo(nome):
    """Devolve o núcleo de um nome com sufixo descritivo, ou None."""
    n = nome.strip()
    for suf in sorted(SUFIXOS, key=len, reverse=True):
        core = n[: -len(suf)].rstrip(" -_.")
        if n.endswith(suf) and len(core) >= 3 and (n[-len(suf) - 1].islower() or n[-len(suf) - 1] in " -_."):
            return core
    return None


def marcas_vigiadas():
    """Marcas de terceiros que o nome não deve conter nem lembrar (config.json, chave marcas_vigiadas)."""
    out = []
    for m in load_json(CONFIG).get("marcas_vigiadas", []):
        if isinstance(m, str):
            m = {"marca": m}
        if (m.get("marca") or "").strip():
            out.append({"marca": m["marca"].strip(), "motivo": (m.get("motivo") or "").strip()})
    return out


def alertas(nome, r, vigiadas=None):
    """Conflitos que a busca exata não mostra: núcleo já registrado e semelhança com marcas vigiadas.

    Cada alerta tem 'resumo' (curto, para a tabela) e 'porque' (a explicação para quem decide).
    """
    out = []
    nuc = (r or {}).get("nucleo")
    if nuc:
        regs = []
        for k in ("9", "42"):
            for x in nuc["classes"].get(k, []):
                regs.append(f"{x['marca'][:25]} ({x['titular'][:30]}, classe {k})")
        regs = list(dict.fromkeys(regs))
        if regs:
            lista = "; ".join(regs[:3]) + (f" e mais {len(regs) - 3}" if len(regs) > 3 else "")
            out.append({
                "resumo": f"núcleo \"{nuc['termo']}\" já é marca",
                "porque": (f"A busca por \"{nome}\" volta vazia, mas \"{nome[len(nuc['termo']):].strip()}\" só descreve o produto. "
                           f"Na análise, o INPI deixa de lado a parte descritiva e compara o resto, \"{nuc['termo']}\", "
                           f"com as marcas que já existem. \"{nuc['termo']}\" já está registrado: {lista}. "
                           "A lei proíbe reproduzir marca alheia \"ainda que com acréscimo\" quando pode haver confusão "
                           "(Lei 9.279/96, art. 124, XIX). O pedido tende a ser negado, e o dono pode se opor."),
            })
    h = handle(nome)
    for m in (marcas_vigiadas() if vigiadas is None else vigiadas):
        mh = handle(m["marca"])
        if mh and (mh in h or (len(mh) >= 5 and h.startswith(mh[:4]))):
            como = "contém" if mh in h else "começa igual a"
            out.append({
                "resumo": f"lembra \"{m['marca']}\"",
                "porque": (f"\"{nome}\" {como} \"{m['marca']}\", uma marca que você marcou como vigiada"
                           + (f" ({m['motivo']})" if m["motivo"] else "") + ". "
                           "A busca exata não acha a semelhança, mas o examinador compara o conjunto pela escrita e pelo som. "
                           "Se a marca vigiada estiver na mesma área, o pedido pode ser negado por risco de confusão "
                           "(Lei 9.279/96, art. 124, XIX), e o dono dela pode se opor."),
            })
    return out


def veredito(r, avisos):
    """Veredito final: um nome limpo na busca com alerta vira 'risco'."""
    if not r:
        return "pendente"
    v = r["veredito"]
    return "risco" if v == "limpo" and avisos else v


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
    vig = marcas_vigiadas()

    rows = []
    for c in cands:
        r = inpi.get(c["nome"])
        av = alertas(c["nome"], r, vig)
        v = veredito(r, av)
        rows.append((ORDEM[v], c["prioridade"], c["nome"], c, r, v, pres.get(c["nome"]), av))
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
        "risco = limpo na busca, mas o núcleo do nome (sem OS, AI, App…) já é marca, ou o nome lembra uma marca vigiada; "
        "tomado = mesma marca ativa. Busca limpa não garante registro: falta a análise fonética.",
        "",
        "**Domínios:** livre? = sem DNS e sem registro na consulta pública (confirmar no registrador); "
        "à venda = estacionado em plataforma de revenda. **GitHub e X:** verificação automática. "
        "**Instagram, TikTok, Facebook e LinkedIn** não respondem sem login: use os links do arquivo tabela.csv.",
        "",
        "| Nome | @ | Origem | Ideia | INPI | Alerta | Classe 9 | Classe 42 | Parecidas | .com | .io | .ai | .com.br | GitHub | X | Nota |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    out_csv = []
    for _, _, _, c, r, v, p, av in rows:
        alerta = "; ".join(a["resumo"] for a in av)
        h = handle(c["nome"])
        c9 = inpi_cell(r["classes"]["9"]) if r else "…"
        c42 = inpi_cell(r["classes"]["42"]) if r else "…"
        sim = similares(r["classes"]) if r else ""
        dom = {d: (p or {}).get("dominios", {}).get(d, "…") for d in DOMAINS}
        gh = (p or {}).get("github", "…")
        xx = (p or {}).get("x", "…")
        md.append(f"| **{c['nome']}** | {h} | {c['origem']} | {c['ideia']} | {v} | {alerta} | {c9} | {c42} | {sim} | "
                  f"{dom['com']} | {dom['io']} | {dom['ai']} | {dom['com.br']} | {gh} | {xx} | {c.get('nota', '')} |")
        links = manual_links(h)
        out_csv.append({
            "nome": c["nome"], "handle": h, "origem": c["origem"], "leva": c.get("leva", ""),
            "prioridade": c["prioridade"], "ideia": c["ideia"], "inpi": v, "alerta": alerta,
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
