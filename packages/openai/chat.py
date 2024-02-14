#--web true
#--param OPENAI_API_KEY $OPENAI_API_KEY
#--param OPENAI_API_HOST $OPENAI_API_HOST

from openai import AzureOpenAI
import re
import requests,socket

ROLE = """
When requested to write code, pick Python.
When requested to show chess position, always use the FEN notation.
When showing HTML, always include what is in the body tag, 
but exclude the code surrounding the actual content. 
So exclude always BODY, HEAD and HTML .
"""

MODEL = "gpt-35-turbo"
AI = None

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"

def notify_slack(message="Hello, World"):
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        print(f"Errore durante l'invio della notifica Slack: {response.text}")
    else:
        print(f"Notifica Slack inviata: {message}")

def get_chess_puzzle():
    url = "https://pychess.run.goorm.io/api/puzzle?limit=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                puzzle = data[0]
                fen = puzzle.get('fen', 'N/A')
                return fen
    except Exception as e:
        print(f"Errore durante la richiesta del puzzle di scacchi: {e}")
    return "Impossibile ottenere il puzzle"
    

def req(msg):
    return [{"role": "system", "content": ROLE}, 
            {"role": "user", "content": msg}]

def ask(input):
    comp = AI.chat.completions.create(model=MODEL, messages=req(input))
    if len(comp.choices) > 0:
        content = comp.choices[0].message.content
        return content
    return "ERROR"


"""
import re
from pathlib import Path
text = Path("util/test/chess.txt").read_text()
text = Path("util/test/html.txt").read_text()
text = Path("util/test/code.txt").read_text()
"""
def extract(text):
    res = {}

    # Aggiunta della ricerca di email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}\b'
    emails = re.findall(email_pattern, text, re.IGNORECASE)
    if emails:
        res['email'] = emails
        for email in emails:
            print(f"Rilevato indirizzo email nell'input: {email}")
            notify_slack()
        return res
    
    # Aggiunta della verifica e risoluzione del dominio in indirizzo IP
    domain_pattern = r'\b((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}\b'
    domains = re.findall(domain_pattern, text, re.IGNORECASE)
    if domains:
        for domain in domains:
            try:
                ip = socket.gethostbyname(domain)
                res['domain'] = domain
                res['ip'] = ip
                print(f"Rilevato dominio {domain} con IP: {ip}")
                notify_slack()
            except socket.gaierror:
                print(f"Impossibile risolvere il dominio: {domain}")
        return res
    
    # Utilizzo di un pattern regex per verificare se la richiesta riguarda scacchi
    chess_pattern = r'\bchess\b|\bscacchi\b'
    if "chess" in text.lower() or "scacchi" in text.lower():
        # Formulazione della domanda per ChatGPT
        chess_question = f"is the following a request for a chess puzzle: \"{text}\": Answer yes or no."
        chatgpt_response = ask(chess_question)       
        # Interpretazione della risposta di ChatGPT
        if "yes" in chatgpt_response.lower():
            notify_slack(f"Richiesta di scacchi ricevuta: {text}")
            fen = get_chess_puzzle()
            if fen != "Impossibile ottenere il puzzle":
                res['chess'] = fen
                notify_slack(f"Puzzle di scacchi generato: {fen}")
            else:
                print(fen)  
        else:
            print("La richiesta non è stata interpretata come una richiesta di puzzle di scacchi.")
        
    return res

    # search for a chess position
    pattern = r'(([rnbqkpRNBQKP1-8]{1,8}/){7}[rnbqkpRNBQKP1-8]{1,8} [bw] (-|K?Q?k?q?) (-|[a-h][36]) \d+ \d+)'
    m = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    #print(m)
    if len(m) > 0:
        res['chess'] = m[0][0]
        return res

    # search for code
    pattern = r"```(\w+)\n(.*?)```"
    m = re.findall(pattern, text, re.DOTALL)
    if len(m) > 0:
        if m[0][0] == "html":
            html = m[0][1]
            # extract the body if any
            pattern = r"<body.*?>(.*?)</body>"
            m = re.findall(pattern, html, re.DOTALL)
            if m:
                html = m[0]
            res['html'] = html
            return res
        res['language'] = m[0][0]
        res['code'] = m[0][1]
        return res
    return res

def main(args):
    global AI
    (key, host) = (args["OPENAI_API_KEY"], args["OPENAI_API_HOST"])
    AI = AzureOpenAI(api_version="2023-12-01-preview", api_key=key, azure_endpoint=host)

    input = args.get("input", "")
    if input == "":
        e_res = {
            "output": "Welcome to the OpenAI demo chat",
            "title": "OpenAI Chat",
            "message": "You can chat with OpenAI."
        }
    else:
        output = ask(input)
        e_res = extract(output)
        # Controlla se sono stati estratti dominio e IP
        domain = e_res.get('domain')
        ip = e_res.get('ip')
        if domain and ip:
            output = ask(f"Assuming {domain} has IP address {ip}, answer to this question: {input}")
        puzzle = e_res.get('chess')

        e_res['output'] = output

    return {"body": e_res }
