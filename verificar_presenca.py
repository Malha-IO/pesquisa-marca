#!/usr/bin/env python3
"""Verificação lenta de domínios (.com, .io, .ai, .com.br) e de nomes no GitHub e no X.

Domínio: com servidor de DNS = registrado (ou à venda, se estacionado em revenda);
sem DNS e sem registro na consulta RDAP = livre?. GitHub e X respondem 404 para
nome livre. Antes de cada rodada, confere com um nome conhecido e um inexistente;
se a checagem de controle falhar, marca a fonte como inconclusiva.
"""
import json
import os
import random
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import tabela_comum as tc

LOG = os.path.join(tc.DIR, "log_presenca.txt")
DELAY = float(os.environ.get("PRES_DELAY", "8"))
IDLE_EXIT = float(os.environ.get("PRES_IDLE_EXIT", str(6 * 3600)))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
PARKING = ("afternic", "sedo", "dan.com", "parking", "bodis", "hugedomains", "undeveloped", "domaincontrol.com.parked")


def log(msg):
    line = f"{datetime.now().strftime('%d/%m %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def pause():
    time.sleep(max(1.0, DELAY + random.uniform(-2, 2)))


def http_status(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:  # noqa: BLE001
        return None


def ns(domain):
    """Servidores de DNS do domínio. DNS via HTTPS (funciona em qualquer sistema); `dig` como reserva."""
    for url in (f"https://cloudflare-dns.com/dns-query?name={domain}&type=NS",
                f"https://dns.google/resolve?name={domain}&type=NS"):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/dns-json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.loads(r.read().decode("utf-8"))
            if j.get("Status") not in (0, 3):  # 0 = ok, 3 = nome não existe
                continue
            return [a["data"].strip().lower() for a in j.get("Answer", []) if a.get("type") == 2]
        except Exception:  # noqa: BLE001
            continue
    try:
        out = subprocess.run(["dig", "+short", "NS", domain], capture_output=True, text=True, timeout=20).stdout
        return [x.strip().lower() for x in out.splitlines() if x.strip()]
    except Exception:  # noqa: BLE001
        return None


def domain_status(domain):
    servers = ns(domain)
    if servers is None:
        return "erro"
    if servers:
        return "à venda" if any(p in s for s in servers for p in PARKING) else "registrado"
    code = http_status(f"https://rdap.org/domain/{domain}")
    pause()
    if code == 200:
        return "registrado"
    return "livre?"


def control_ok(url_tpl):
    taken = http_status(url_tpl.format("nike"))
    time.sleep(2)
    free = http_status(url_tpl.format("zqxjvtessa9183"))
    return taken == 200 and free == 404


def profile(url_tpl, h, ok):
    if not ok:
        return "inconclusivo"
    code = http_status(url_tpl.format(h))
    if code == 200:
        return "ocupado"
    if code == 404:
        return "livre"
    return "inconclusivo"


GH = "https://github.com/{}"
XX = "https://x.com/{}"


def main():
    res = tc.load_json(tc.RES_PRES)
    last_new = time.time()
    controls = None
    controls_at = 0
    while True:
        cands = tc.load_csv()
        todo = sorted([c for c in cands if c["nome"] not in res], key=lambda c: (c["prioridade"], c["nome"]))
        done = len(cands) - len(todo)
        tc.set_status("presenca", f"{done} de {len(cands)} verificados" + (", rodando" if todo else ", aguardando nomes novos"))
        tc.write_table()
        if not todo:
            if time.time() - last_new > IDLE_EXIT:
                tc.set_status("presenca", f"{done} de {len(cands)} verificados; encerrado")
                tc.write_table()
                log("nada novo há horas; encerrando")
                return
            time.sleep(300)
            continue
        last_new = time.time()
        if controls is None or time.time() - controls_at > 1800:
            controls = {"github": control_ok(GH), "x": control_ok(XX)}
            controls_at = time.time()
            log(f"checagem de controle: {controls}")
            pause()
        c = todo[0]
        h = tc.handle(c["nome"])
        log(f"verificando {c['nome']} ({h})")
        doms = {}
        for d in tc.DOMAINS:
            doms[d] = domain_status(f"{h}.{d}")
            pause()
        gh = profile(GH, h, controls["github"])
        pause()
        xx = profile(XX, h, controls["x"])
        pause()
        res[c["nome"]] = {"handle": h, "dominios": doms, "github": gh, "x": xx,
                          "checado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        tc.save_json(tc.RES_PRES, res)
        log(f"{c['nome']}: {doms} github={gh} x={xx}")


if __name__ == "__main__":
    main()
