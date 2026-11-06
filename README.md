# Pesquisa de marca

Ferramenta pequena para escolher o nome de um produto. Você mantém uma lista de candidatos, e dois processos verificam cada nome devagar, em segundo plano:

- **INPI:** busca exata e por radical nas classes 9 (software) e 42 (serviços de software e SaaS).
- **Internet:** domínios .com, .io, .ai e .com.br, e nomes no GitHub e no X.

Uma página no navegador mostra o andamento, filtra os nomes e deixa você adicionar candidatos e marcar favoritos.

Feita pela [Malha.io](https://malha.io) e compartilhada com as startups do Amplifier Batch #11.

## Do que precisa

Python 3.8 ou mais novo. Não há nada para instalar além disso.

- **Mac:** abra o Terminal e digite `python3 --version`. Se não aparecer uma versão, instale pelo site [python.org](https://www.python.org/downloads/).
- **Windows:** instale pelo site [python.org](https://www.python.org/downloads/) e marque **"Add python.exe to PATH"** na primeira tela do instalador.
- **Linux:** o Python 3 já vem instalado na maioria das distribuições.

## Como iniciar

1. Baixe o projeto. No GitHub, clique em **Code** e depois em **Download ZIP**, e descompacte. Quem usa git pode rodar `git clone https://github.com/Malha-IO/pesquisa-marca.git`.
2. Inicie:
   - **Mac:** clique duas vezes em `iniciar.command`. Na primeira vez, o Mac pode bloquear. Nesse caso, clique com o botão direito, escolha **Abrir** e confirme.
   - **Windows:** clique duas vezes em `iniciar.bat`.
   - **Qualquer sistema, pelo terminal:** entre na pasta e rode `python3 iniciar.py`. No Windows, `py -3 iniciar.py`.
3. A página abre sozinha no navegador, em `http://localhost:8765`.

Deixe a janela do terminal aberta enquanto a pesquisa roda. Ctrl+C encerra tudo. O que já foi pesquisado fica salvo, e rodar de novo continua de onde parou.

## Como colocar os seus nomes

A lista vem com três exemplos: Farol, Ponte e Nimbo. Troque pelos seus de um destes dois jeitos.

### Pela página, um nome de cada vez

1. Com a ferramenta rodando, abra **Adicionar nome à pesquisa**, logo abaixo dos medidores.
2. Preencha:
   - **Nome:** a palavra que você quer testar, até 40 caracteres, sem vírgula nem aspas.
   - **Origem:** de onde vem a palavra. Serve só para filtrar depois.
   - **Ideia:** o que o nome conta sobre o produto. Ajuda na hora de comparar.
   - **Prioridade:** 1 é verificada primeiro, 3 por último.
3. Clique em **Adicionar**. O nome entra na fila e os processos pegam na próxima volta.

Não precisa reiniciar nada. Nome repetido é recusado.

### Pelo arquivo, vários de uma vez

Para colar uma lista grande, edite `candidatos.csv`, que fica na pasta do projeto. Cada linha é um nome:

```csv
nome,origem,leva,ideia,prioridade,nota
Aurora,latim,1,o começo do dia,1,
Kora,inventado,1,curto e sonoro,2,
Vertice,italiano,2,o ponto mais alto,3,soa como vértice
```

- **Só a coluna `nome` é obrigatória.** As outras podem ficar vazias, mas as vírgulas precisam continuar lá.
- **Apague as linhas de exemplo** se não quiser que elas sejam pesquisadas.
- **Se um texto tiver vírgula, coloque entre aspas:** `"curto, sonoro e fácil"`.
- **Use um editor de texto simples**, como o TextEdit do Mac em modo de texto puro, o Bloco de Notas do Windows ou o VS Code. O Excel costuma mudar a codificação e estragar os acentos. Se preferir planilha, use o Google Planilhas e baixe como CSV.
- **Salve o arquivo.** A ferramenta relê a lista sozinha, e não precisa parar nada.

### Outros ajustes

- **Começar do zero:** pare a ferramenta e apague `resultados.json` e `presenca.json`.
- **Trocar o título da página:** edite `config.json`.
- **Baixar a planilha com os resultados:** botão **Baixar planilha** na página, ou o arquivo `tabela.csv`.

## Como ler os resultados

| Coluna | O que quer dizer |
|---|---|
| INPI **limpo** | Nenhuma marca ativa com esse nome nas classes 9 e 42. |
| INPI **ressalva** | Existe marca parecida ativa, ou um registro antigo em vigor. Vale olhar. |
| INPI **tomado** | A mesma marca está ativa na classe. |
| Domínio **livre?** | Sem DNS e sem registro na consulta pública. Confirme no registrador antes de contar com ele. |
| Domínio **à venda** | Registrado por quem revende domínios. Dá para comprar, mas costuma ser caro. |
| GitHub e X **livre** | O perfil não existe. No X, pode ser conta suspensa ou reservada. |

Instagram, TikTok, Facebook e LinkedIn não respondem sem login. Por isso a página traz um link para cada nome: um clique mostra se o perfil existe.

## Limites que importam

- **Busca limpa não garante registro.** O INPI compara também pelo som das palavras, e a busca só acha a grafia. Antes de depositar, peça o parecer de um agente de propriedade industrial.
- **A pesquisa é lenta de propósito.** São 90 segundos entre buscas no INPI. Consultas em sequência fazem o site recusar a conexão por um tempo. Se isso acontecer, o processo espera e tenta de novo sozinho, de 5 a 30 minutos depois.
- **Não registre o nome junto com uma marca de terceiros.** Se uma parte do nome já é marca de outra empresa na mesma classe, o INPI tende a negar o conjunto inteiro.

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `iniciar.py`, `iniciar.command`, `iniciar.bat` | Sobem tudo e abrem a página. |
| `app.py`, `index.html` | A página. |
| `verificar_inpi.py` | A pesquisa no INPI. |
| `verificar_presenca.py` | A pesquisa de domínios, GitHub e X. |
| `tabela_comum.py` | Lista, resultados e planilha. |
| `candidatos.csv` | A lista de nomes. |
| `resultados.json`, `presenca.json` | O que já foi pesquisado. |
| `config.json` | Título da página. |

## Licença

Apache 2.0. Veja o arquivo `LICENSE`.
