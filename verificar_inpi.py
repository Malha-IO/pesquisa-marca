#!/usr/bin/env python3
"""Consulta lenta de candidatos a marca no pePI do INPI (classes 9 e 42).

Lê candidatos.csv a cada volta, consulta os nomes ainda não verificados,
grava resultados.json e reescreve tabela.md. Espera entre consultas e
recua quando o INPI recusa conexão. Só biblioteca padrão.
"""
import csv
import html
import http.cookiejar
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(DIR, "candidatos.csv")
RES = os.path.join(DIR, "resultados.json")
TAB = os.path.join(DIR, "tabela.md")
LOG = os.path.join(DIR, "log.txt")

BASE = "https://busca.inpi.gov.br/pePI"
CLASSES = ("9", "42")
DELAY = float(os.environ.get("INPI_DELAY", "45"))      # segundos entre consultas
JITTER = 15.0
BACKOFF = [300, 600, 1200, 1800]                         # recuo em falha de rede
IDLE_EXIT = float(os.environ.get("INPI_IDLE_EXIT", str(3 * 3600)))  # sai se nada novo por 3h
MAX_FAIL = float(os.environ.get("INPI_MAX_FAIL", str(12 * 3600)))   # desiste após 12h só com falhas
# Marca notória usada para confirmar que a busca e a leitura da página funcionam antes de confiar nos resultados.
CONTROL_MARK = os.environ.get("INPI_CONTROLE_MARCA", "GOOGLE")
CONTROL_HOLDER = os.environ.get("INPI_CONTROLE_TITULAR", "GOOGLE").upper()
DEAD = re.compile(r"extint|arquivad|indeferid|cancelad|nulidade", re.I)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def log(msg):
    line = f"{datetime.now().strftime('%d/%m %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def norm(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper()


class NetError(Exception):
    pass


class Inpi:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.op.addheaders = [("User-Agent", UA), ("Accept-Language", "pt-BR,pt;q=0.9")]
        self.ok = False

    def _get(self, url, data=None):
        try:
            with self.op.open(url, data=data, timeout=60) as r:
                return r.read().decode("iso-8859-1", "replace")
        except Exception as e:  # noqa: BLE001
            raise NetError(repr(e)[:200])

    def login(self):
        self._get(f"{BASE}/")
        time.sleep(3)
        self._get(f"{BASE}/servlet/LoginController?action=login")
        time.sleep(3)
        self._get(f"{BASE}/jsp/marcas/Pesquisa_classe_basica.jsp")
        self.ok = True

    def search(self, marca, cls, exata):
        if not self.ok:
            self.login()
        body = urllib.parse.urlencode({
            "buscaExata": "sim" if exata else "nao", "txt": "", "marca": marca,
            "classeInter": cls, "registerPerPage": "100", "botao": " pesquisar » ",
            "Action": "searchMarca", "tipoPesquisa": "BY_MARCA_CLASSIF_BASICA",
        }, encoding="iso-8859-1").encode("ascii")
        page = self._get(f"{BASE}/servlet/MarcasServletController", body)
        if "RESULTADO DA PESQUISA" not in page and "Nenhum" not in page:
            # sessão caiu: refaz login uma vez
            self.ok = False
            self.login()
            page = self._get(f"{BASE}/servlet/MarcasServletController", body)
            if "RESULTADO DA PESQUISA" not in page and "Nenhum" not in page:
                raise NetError("resposta sem resultado (sessão ou layout mudou)")
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
            tds = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", td))).strip()
                   for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]
            if len(tds) >= 8 and re.match(r"^\d", tds[0]):
                rows.append({"processo": tds[0], "marca": tds[3], "situacao": tds[5],
                             "titular": tds[6], "classe": tds[7]})
        return rows


def pause():
    time.sleep(DELAY + random.uniform(-JITTER, JITTER))


def check_name(inpi, nome):
    key = norm(nome)
    out = {}
    for cls in CLASSES:
        ex = inpi.search(nome, cls, True)
        pause()
        rad = inpi.search(nome, cls, False)
        pause()
        live_ex = [r for r in ex if not DEAD.search(r["situacao"])]
        word = re.compile(r"(^|[^A-Z0-9])" + re.escape(key))
        live_rad = [r for r in rad
                    if not DEAD.search(r["situacao"]) and "NCL" in r["classe"]
                    and word.search(norm(r["marca"])) and norm(r["marca"]).strip() != key]
        out[cls] = {
            "exata_total": len(ex),
            "exata_ativas_ncl": [r for r in live_ex if "NCL" in r["classe"]],
            "exata_ativas_antigas": [r for r in live_ex if "NCL" not in r["classe"]],
            "radical_ativas": live_rad,
        }
    if any(out[c]["exata_ativas_ncl"] for c in CLASSES):
        verdict = "tomado"
    elif any(out[c]["radical_ativas"] or out[c]["exata_ativas_antigas"] for c in CLASSES):
        verdict = "ressalva"
    else:
        verdict = "limpo"
    return {"veredito": verdict, "classes": out,
            "checado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def load_csv():
    with open(CSV, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("nome", "").strip()]
    for r in rows:
        r["nome"] = r["nome"].strip()
        r["prioridade"] = int(r.get("prioridade") or 3)
    return rows


def load_res():
    if os.path.exists(RES):
        with open(RES, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_res(res):
    tmp = RES + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    os.replace(tmp, RES)


def write_table(cands, res, status):
    """Grava o estado do INPI e redesenha a tabela comum (MD e CSV)."""
    import tabela_comum as tc
    tc.set_status("inpi", status)
    tc.write_table()


def main():
    inpi = Inpi()
    res = load_res()
    last_new = time.time()
    fail_since = None
    step = 0
    validated = False
    while True:
        cands = load_csv()
        todo = sorted([c for c in cands if c["nome"] not in res], key=lambda c: (c["prioridade"], c["nome"]))
        done = len(cands) - len(todo)
        write_table(cands, res, f"{done} de {len(cands)} verificados" + (", rodando" if todo else ", aguardando nomes novos"))
        if not todo:
            if time.time() - last_new > IDLE_EXIT:
                log("nada novo há horas; encerrando")
                write_table(cands, res, f"{done} de {len(cands)} verificados; encerrado")
                return
            time.sleep(300)
            continue
        last_new = time.time()
        try:
            if not validated:
                rows = inpi.search(CONTROL_MARK, "42", True)
                if not any(CONTROL_HOLDER in r["titular"].upper() and not DEAD.search(r["situacao"]) for r in rows):
                    raise NetError(f"checagem de controle falhou: {CONTROL_MARK}/42 não achou {CONTROL_HOLDER} ativo")
                validated = True
                log(f"checagem de controle ok ({CONTROL_MARK}/42)")
                pause()
            c = todo[0]
            log(f"consultando {c['nome']}")
            res[c["nome"]] = check_name(inpi, c["nome"])
            save_res(res)
            log(f"{c['nome']}: {res[c['nome']]['veredito']}")
            fail_since = None
            step = 0
        except NetError as e:
            inpi.ok = False
            validated = False
            fail_since = fail_since or time.time()
            if time.time() - fail_since > MAX_FAIL:
                log(f"INPI indisponível há mais de {MAX_FAIL/3600:.0f}h; encerrando")
                write_table(cands, res, f"{done} de {len(cands)} verificados; encerrado por indisponibilidade do INPI")
                sys.exit(2)
            wait = BACKOFF[min(step, len(BACKOFF) - 1)]
            step += 1
            log(f"falha: {e}; nova tentativa em {wait // 60} min")
            write_table(cands, res, f"{done} de {len(cands)} verificados; INPI recusando conexão, nova tentativa às "
                        f"{datetime.fromtimestamp(time.time() + wait).strftime('%H:%M')}")
            time.sleep(wait)


if __name__ == "__main__":
    main()
