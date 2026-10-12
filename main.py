import os
import sys
import json
import base64
import operator
from typing import TypedDict, Annotated, List, Union

from fastapi import FastAPI, Request, BackgroundTasks, Response
import httpx

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from supabase import create_client, Client
from fpdf import FPDF

app = FastAPI(title="DG-AGENT-CORE-SAAS", version="4.0.0")

# ==========================================
# 0. CONFIGURATION & CLÉS API
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# PROMPT SYSTÈME VERROUILLÉ (CADRAGE STRICT ET IMMUABLE)
SYSTEM_PROMPT = """Tu es Amal-DG, Directrice Générale et Architecte IA du SaaS Immobilier Québec BailConforme.ca.

CADRAGE STRICT DU PROJET :
- Projet : BailConforme.ca (SaaS B2B de gestion de baux immobiliers, conformité TAL, Loi 25 et Code civil du Québec).
- Mission : Orchestrer en autonomie totale la réalisation des études 360°, la conception et la livraison du projet.
- Règle d'or : Ne perds JAMAIS ce contexte. Ne réponds jamais sur des généralités SaaS B2B ou d'autres marchés.

FORMAT DE RÉPONSE POUR EXÉCUTER UNE ACTION :
Réponds EXCLUSIVEMENT sous forme d'un objet JSON valide (aucun texte autour) :
{
  "action": "nom_outil",
  "action_input": { ...arguments... }
}

OUTILS DISPONIBLES :
1. `delegate_to_subagent` : Délègue un volet d'analyse à une équipe spécialisée.
   Arguments : {"team": "team3_product", "task_description": "...", "save_to_file": "docs/analyse_360/01_produit.md"}
2. `read_github_file` : Lit un fichier de consignes .md ou un livrable sur GitHub.
   Arguments : {"file_path": "docs/rules.md"}
3. `git_commit_and_push` : Enregistre/déploie un fichier sur GitHub.
   Arguments : {"file_path": "...", "commit_message": "...", "content_to_write": "..."}
4. `compile_markdowns_to_pdf` : Compile l'ensemble des rapports Markdown en un document PDF Master.
   Arguments : {"output_pdf_path": "BailConforme_Analyse_360_Master.pdf"}
5. `tavily_web_search` : Effectue une recherche web ciblée.
   Arguments : {"query": "..."}

LES 8 PÔLES À EXÉCUTER :
- `team3_product` (Produit & R&D) ➔ `docs/analyse_360/01_produit.md`
- `team_dev` (Dev & Architecture) ➔ `docs/analyse_360/02_architecture.md`
- `team5_growth_seo` (Growth & SEO) ➔ `docs/analyse_360/03_growth.md`
- `team_sales` (Ventes & ABM) ➔ `docs/analyse_360/04_ventes_abm.md`
- `team_finance` (Finance & Pricing) ➔ `docs/analyse_360/05_finance.md`
- `team_legal` (Juridique & Conformité TAL/Loi 25) ➔ `docs/analyse_360/06_conformite.md`
- `team_ux` (UX/UI & Design) ➔ `docs/analyse_360/07_ux_design.md`
- `team_secops` (SecOps & Souveraineté) ➔ `docs/analyse_360/08_secops.md`

Si toutes tes actions sont terminées et que tu t'adresses directement à l'utilisateur sur Slack, réponds en TEXTE NORMAL."""

# ==========================================
# 1. DÉFINITION DES OUTILS
# ==========================================

def read_github_file(file_path: str) -> str:
    """Lit un fichier .md de consignes ou de rapport sur GitHub."""
    try:
        if not GITHUB_TOKEN or not GITHUB_REPO:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            return "Fichier non trouvé en local."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
        with httpx.Client() as client:
            resp = client.get(api_url, headers=headers)
            if resp.status_code == 200:
                content_b64 = resp.json().get("content", "")
                return base64.b64decode(content_b64).decode("utf-8")
            return f"Fichier non trouvé sur GitHub (code {resp.status_code})."
    except Exception as e:
        return f"Erreur lecture GitHub: {str(e)}"

def git_commit_and_push(file_path: str, commit_message: str, content_to_write: Union[str, bytes]) -> str:
    """Publie ou met à jour n'importe quel fichier sur GitHub."""
    try:
        safe_path = os.path.normpath(file_path).replace("\\", "/")
        os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)
        
        if isinstance(content_to_write, bytes):
            with open(safe_path, "wb") as f: f.write(content_to_write)
            content_b64 = base64.b64encode(content_to_write).decode("utf-8")
        else:
            with open(safe_path, "w", encoding="utf-8") as f: f.write(content_to_write)
            content_b64 = base64.b64encode(content_to_write.encode("utf-8")).decode("utf-8")

        if not GITHUB_TOKEN or not GITHUB_REPO:
            return f"Fichier {file_path} créé en local (variables GitHub absentes)."

        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{safe_path}"

        with httpx.Client() as client:
            get_resp = client.get(api_url, headers=headers)
            payload = {"message": commit_message, "content": content_b64, "branch": "main"}
            if get_resp.status_code == 200:
                payload["sha"] = get_resp.json().get("sha")
            client.put(api_url, json=payload, headers=headers)

        return f"SUCCÈS: Fichier {file_path} publié/déployé sur GitHub."
    except Exception as e:
        return f"ERREUR GITHUB: {str(e)}"

def delegate_to_subagent(team: str, task_description: str, save_to_file: str = "") -> str:
    """Délègue une étude à un sous-agent OpenRouter et enregistre le Markdown."""
    try:
        model_name = "google/gemma-4-31b:free"
        sub_client = ChatOpenAI(
            model=model_name,
            temperature=0.2,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1"
        )
        
        system_msg = SystemMessage(content=f"Tu es l'équipe {team} experte pour BailConforme.ca (SaaS Immobilier Québec). Rédige une étude approfondie et exhaustive au format Markdown.")
        user_msg = HumanMessage(content=task_description)
        
        response = sub_client.invoke([system_msg, user_msg])
        result_text = response.content
        
        if save_to_file:
            git_commit_and_push(save_to_file, f"Livrable {team}", result_text)
            return f"SUCCÈS: Rapport de l'équipe {team} publié dans '{save_to_file}' sur GitHub."
            
        return result_text[:2000]
    except Exception as e:
        return f"ERREUR DÉLÉGATION {team}: {str(e)}"

def compile_markdowns_to_pdf(output_pdf_path: str = "BailConforme_Analyse_360_Master.pdf") -> str:
    """Compile tous les rapports Markdown de docs/analyse_360/ en un PDF Master."""
    try:
        folder_path = "docs/analyse_360"
        if not os.path.exists(folder_path):
            return f"ERREUR: Dossier {folder_path} introuvable."

        files = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".md")])
        if not files:
            return "ERREUR: Aucun rapport Markdown trouvé."

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Page de titre
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 30, "BailConforme.ca - Master Plan & Document 360°", ln=True, align="C")
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, "Document Maître rédigé et orchestré par Amal-DG", ln=True, align="C")
        pdf.ln(15)

        for file in files:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, f"Section : {os.path.basename(file)}", ln=True)
            pdf.ln(4)
            
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()

            pdf.set_font("Helvetica", "", 10)
            safe_text = content.encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 5, safe_text)

        pdf_bytes = pdf.output()
        return git_commit_and_push(output_pdf_path, "Feat: Document Master PDF 360°", pdf_bytes)
    except Exception as e:
        return f"ERREUR COMPILATION PDF: {str(e)}"

def tavily_web_search(query: str) -> str:
    if not TAVILY_API_KEY: return "Clé Tavily non configurée."
    try:
        with httpx.Client() as client:
            res = client.post("https://api.tavily.com/search", json={"api_key": TAVILY_API_KEY, "query": query}, timeout=10.0)
            return res.json().get("answer", "Aucun résultat.")[:1000]
    except Exception as e:
        return f"Erreur Tavily: {str(e)}"

TOOLS_MAP = {
    "delegate_to_subagent": delegate_to_subagent,
    "read_github_file": read_github_file,
    "git_commit_and_push": git_commit_and_push,
    "compile_markdowns_to_pdf": compile_markdowns_to_pdf,
    "tavily_web_search": tavily_web_search
}

# ==========================================
# 2. GESTION DE MÉMOIRE ET MOTEUR LANGGRAPH
# ==========================================

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, groq_api_key=GROQ_API_KEY)

def prepare_optimized_context(messages: list) -> list:
    """Optimise la fenêtre de contexte en tronquant les sorties d'outils volumineuses."""
    cleaned = []
    for msg in messages:
        if isinstance(msg, HumanMessage) and "--- RÉSULTAT ACTION" in msg.content:
            if len(msg.content) > 400:
                short_text = msg.content[:200] + "\n... [Résultat complet sauvegardé dans le fichier sur GitHub] ..."
                cleaned.append(HumanMessage(content=short_text))
            else:
                cleaned.append(msg)
        else:
            cleaned.append(msg)
    # Conservation des 8 derniers messages significatifs
    return cleaned[-8:]

def call_model(state: AgentState):
    system_ctx = SystemMessage(content=SYSTEM_PROMPT)
    optimized_history = prepare_optimized_context(state["messages"])
    
    full_messages = [system_ctx] + optimized_history
    response = llm.invoke(full_messages)
    content = response.content.strip()
    
    if content.startswith("{") and "action" in content:
        try:
            tool_data = json.loads(content)
            action_name = tool_data.get("action")
            action_input = tool_data.get("action_input", {})
            
            if action_name in TOOLS_MAP:
                tool_fn = TOOLS_MAP[action_name]
                tool_result = tool_fn(**action_input) if isinstance(action_input, dict) else tool_fn(action_input)
                
                tool_msg = HumanMessage(content=f"--- RÉSULTAT ACTION ({action_name}) ---\n{tool_result}\n\nPoursuis la suite des opérations de façon autonome.")
                return {"messages": [AIMessage(content=content), tool_msg]}
        except Exception:
            pass

    return {"messages": [response]}

def should_continue(state: AgentState):
    """Boucle automatique tant qu'une action est exécutée."""
    last_message = state["messages"][-1]
    if isinstance(last_message, HumanMessage) and "--- RÉSULTAT ACTION" in last_message.content:
        return "agent"
    return END

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"agent": "agent", END: END})

app_graph = workflow.compile()

# ==========================================
# 3. FASTAPI ET SLACK INTEGRATION
# ==========================================

def process_slack_mission_async(channel_id: str, user_prompt: str):
    conversation_history = [HumanMessage(content=user_prompt)]
    try:
        final_state = app_graph.invoke({"messages": conversation_history})
        final_message = final_state["messages"][-1].content
    except Exception as e:
        final_message = f"⚠️ *Erreur Moteur Amal-DG* : {str(e)}"

    if SLACK_TOKEN:
        try:
            httpx.post(
                "https://slack.com/api/chat.postMessage",
                json={"channel": channel_id, "text": final_message},
                headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"}
            )
        except: pass

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if data.get("type") == "url_verification": return {"challenge": data.get("challenge")}
        
    event = data.get("event", {})
    if event.get("type") in ["message", "app_mention"] and not event.get("bot_id"):
        channel_id = event.get("channel")
        user_prompt = event.get("text")
        if channel_id and user_prompt:
            background_tasks.add_task(process_slack_mission_async, channel_id, user_prompt)

    return Response(status_code=200)

@app.get("/health")
def health_check():
    return {"status": "SAAS-ENGINE-ONLINE-V4-OPTIMIZED"}
