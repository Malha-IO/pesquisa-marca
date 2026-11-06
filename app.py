#!/usr/bin/env python3
"""Página local para acompanhar os candidatos a marca.

Lê os resultados gravados pelos processos de pesquisa (INPI, domínios e redes),
permite adicionar nomes à lista e marcar favoritos. Só biblioteca padrão.

    python3 app.py            # http://localhost:8765
"""
import csv
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import tabela_comum as tc

PORT = int(os.environ.get("PORT", "8765"))
FAV = os.path.join(tc.DIR, "favoritos.json")
INDEX = os.path.join(tc.DIR, "index.html")
LOCK = threading.Lock()
FIELDS = ["nome", "origem", "leva", "ideia", "prioridade", "nota"]


def data():
    cands = tc.load_csv()
    inpi = tc.load_json(tc.RES_INPI)
    pres = tc.load_json(tc.RES_PRES)
    favs = tc.load_json(FAV).get("favoritos", [])
    items = []
    for c in cands:
        r = inpi.get(c["nome"])
        p = pres.get(c["nome"])
        h = tc.handle(c["nome"])
        items.append({
            "nome": c["nome"], "handle": h, "origem": c.get("origem", ""), "leva": c.get("leva", ""),
            "ideia": c.get("ideia", ""), "prioridade": c["prioridade"], "nota": c.get("nota", ""),
            "favorito": c["nome"] in favs,
            "inpi": r["veredito"] if r else "pendente",
            "classe9": tc.inpi_cell(r["classes"]["9"]) if r else None,
            "classe42": tc.inpi_cell(r["classes"]["42"]) if r else None,
            "parecidas": tc.similares(r["classes"]) if r else "",
            "dominios": (p or {}).get("dominios"),
            "github": (p or {}).get("github"),
            "x": (p or {}).get("x"),
            "links": tc.manual_links(h),
        })
    st = tc.load_json(tc.STATUS)
    cfg = tc.load_json(os.path.join(tc.DIR, "config.json"))
    return {
        "config": {"titulo": cfg.get("titulo", "Marca do produto"),
                   "subtitulo": cfg.get("subtitulo", ""), "rotulo": cfg.get("rotulo", "")},
        "status": {"inpi": st.get("inpi", "não iniciado"), "presenca": st.get("presenca", "não iniciado")},
        "total": len(items),
        "inpi_feitos": sum(1 for i in items if i["inpi"] != "pendente"),
        "presenca_feitos": sum(1 for i in items if i["dominios"]),
        "itens": items,
    }


def add_candidate(body):
    nome = (body.get("nome") or "").strip()
    if not nome or len(nome) > 40 or any(ch in nome for ch in ",\n\r\""):
        return 400, {"erro": "Informe um nome de até 40 caracteres, sem vírgula nem aspas."}
    with LOCK:
        existing = {c["nome"].lower() for c in tc.load_csv()}
        if nome.lower() in existing:
            return 409, {"erro": f"{nome} já está na lista."}
        row = {
            "nome": nome,
            "origem": (body.get("origem") or "inventado").strip()[:30],
            "leva": "web",
            "ideia": (body.get("ideia") or "").strip()[:160],
            "prioridade": str(body.get("prioridade") or 1),
            "nota": "adicionado pela página",
        }
        with open(tc.CSV_IN, "rb") as f:
            f.seek(0, os.SEEK_END)
            needs_nl = False
            if f.tell() > 0:
                f.seek(-1, os.SEEK_END)
                needs_nl = f.read(1) != b"\n"
        with open(tc.CSV_IN, "a", encoding="utf-8", newline="") as f:
            if needs_nl:
                f.write("\n")
            csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n").writerow(row)
    return 201, {"ok": True, "nome": nome}


def toggle_fav(body):
    nome = (body.get("nome") or "").strip()
    with LOCK:
        favs = tc.load_json(FAV).get("favoritos", [])
        if nome in favs:
            favs.remove(nome)
        else:
            favs.append(nome)
        tc.save_json(FAV, {"favoritos": favs})
    return 200, {"ok": True, "favorito": nome in favs}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload, ctype="application/json; charset=utf-8"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(INDEX, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if self.path.startswith("/api/data"):
            return self._send(200, data())
        if self.path == "/tabela.csv":
            with open(tc.TAB_CSV, "rb") as f:
                return self._send(200, f.read(), "text/csv; charset=utf-8")
        return self._send(404, {"erro": "não encontrado"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, {"erro": "JSON inválido"})
        if self.path == "/api/candidato":
            return self._send(*add_candidate(body))
        if self.path == "/api/favorito":
            return self._send(*toggle_fav(body))
        return self._send(404, {"erro": "não encontrado"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"Marca: http://localhost:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
