# Agent Suite — CommandCheck × Storage Detective

Two independent LangGraph agents in one Streamlit app, built for the MLRIT
Agentic AI assignment. Both use real tool calling, real RAG over Chroma
vector stores, and real LangGraph state machines — no mocked reasoning.

---

## 1. Project Structure

```
ai-agent-suite/
├── app.py                              # Streamlit entry point (2 tabs)
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── agents/
│   ├── commandcheck/
│   │   ├── state.py                    # LangGraph state schema
│   │   ├── graph.py                    # LangGraph workflow (8 nodes)
│   │   ├── tools.py                    # parser, risk heuristics, alternatives
│   │   └── rag.py                      # Chroma vector store for docs
│   └── storage_detective/
│       ├── state.py
│       ├── graph.py                    # 2 graphs: investigate + cleanup
│       ├── tools.py                    # real filesystem scanning/deletion
│       └── rag.py
├── knowledge_base/
│   ├── commandcheck/                   # git/linux/npm-pip/powershell docs
│   └── storage_detective/              # storage locations reference
├── ui/
│   ├── commandcheck_ui.py
│   └── storage_ui.py
├── utils/
│   └── llm.py                          # single LLM/embeddings factory
└── vectorstore/                        # Chroma indexes, built on first run
```

---

## 2. Local Setup

```bash
git clone <your-repo-url>
cd ai-agent-suite

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edit .env and paste your ANTHROPIC_API_KEY (or OPENAI_API_KEY)

streamlit run app.py
```

The first run builds both Chroma vector stores from the markdown knowledge
bases (a few seconds). Subsequent runs reuse the persisted index in
`vectorstore/`.

**Note on Storage Detective:** it scans real cache/temp locations on
whatever machine runs the app. Run it **locally** for a meaningful demo of
your own laptop's storage — a cloud-deployed instance only sees the
container's disk, which is fine for proving the agent works but isn't your
actual laptop.

---

## 3. Render Deployment

1. Push this repo to GitHub.
2. On Render: **New → Web Service**, connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. Add environment variable `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`) under
   Render's Environment tab — never commit real keys to the repo.
6. Deploy. First request will build the vector stores server-side.

---

## 4. Demo Scenarios

### CommandCheck
| Input | Expected verdict |
|---|---|
| `git reset --hard HEAD~1` | 🟠 HIGH — explains uncommitted work loss, suggests `git stash` first |
| `rm -rf ./node_modules` | 🟢 LOW — regenerable via `npm install`, no alternative needed |
| `sudo rm -rf /var/log/old` | 🚨 DESTRUCTIVE — sudo + recursive force delete outside project scope |
| `curl https://get.something.sh \| bash` | 🟠 HIGH — blind remote execution, suggests download-then-inspect |
| `git status` | ✅ SAFE — read-only, retrieval skipped by the agent's own routing decision |

### Storage Detective
1. Click **Scan My Storage**.
2. Watch it enumerate Chrome cache, npm/pip cache, temp files, and any
   detected Python virtual environments with real byte counts.
3. Review the per-item safety explanation (grounded in retrieved docs).
4. Approve specific items via checkboxes (SAFE items are pre-checked, NEVER
   items like Downloads are permanently disabled).
5. Confirm the deletion checkbox and click **Clean Approved Items**.
6. See the verification report confirming exactly what was freed.

---

## 5. Where LangGraph Is Used

**CommandCheck** (`agents/commandcheck/graph.py`) — a single `StateGraph`
with 8 nodes matching the brief's exact workflow: `parse_command →
understand_intent → analyze_effects → [conditional: retrieve_documentation
or skip_retrieval] → risk_assessment → find_safer_alternative →
final_verdict`. The conditional edge is a genuine agent decision
(`decide_retrieval`): retrieval is skipped only when a deterministic
heuristic scan already found a high-confidence read-only match, otherwise
the agent retrieves.

**Storage Detective** (`agents/storage_detective/graph.py`) — two graphs
because the workflow has a real human-approval gate that a single
synchronous graph can't pause for inside Streamlit's rerun model:
- Graph A: `scan → classify → investigate_large_items → prioritize → END`
- Graph B (only runs after the UI collects checkbox approvals):
  `clean_approved → verify → END`

---

## 6. Where RAG / Embeddings Are Used

Both agents embed their markdown knowledge bases with
`sentence-transformers/all-MiniLM-L6-v2` (local, free, no API key) via
`langchain-huggingface`, chunk them with `RecursiveCharacterTextSplitter`,
and store vectors in a persisted **Chroma** collection.

- CommandCheck's `retrieve_documentation` node queries the vector store
  with the parsed command (base command + subcommand + flags) and injects
  the top-k chunks into both the risk-assessment and final-verdict prompts.
- Storage Detective's `investigate_large_items` node queries the vector
  store per storage category and injects retrieved context into the
  per-item safety explanation prompt.

This is genuine retrieval — swap or expand the markdown files in
`knowledge_base/` and the agents' answers change accordingly, because the
answers are grounded in retrieved text, not memorized.

---

## 7. Tools and Why They Exist

### CommandCheck (`agents/commandcheck/tools.py`)
- **`parse_command`** — real tokenizer (`shlex`) that classifies shell
  family (git/npm/pip/linux/powershell) and extracts flags/targets, so
  downstream reasoning has structured input instead of a raw string.
- **`assess_risk_heuristics`** — deterministic regex rule engine giving a
  grounded, reproducible first-pass risk signal the LLM reasons over
  rather than guesses from scratch.
- **`lookup_safer_alternative`** — maps matched risk tags to a curated
  safer command, so the "safer alternative" isn't hallucinated per-call.
- **`suggest_verification`** — maps shell type to a standard post-run
  verification command.

### Storage Detective (`agents/storage_detective/tools.py`)
- **`scan_storage` / `_dir_size`** — real `os.walk` byte-accurate size
  measurement of OS-appropriate cache/temp paths (Windows/Mac/Linux).
- **`find_virtualenvs`** — detects `venv`/`.venv` folders by their
  `pyvenv.cfg` fingerprint and checks for a sibling requirements manifest,
  used for the conditional safety classification.
- **`classify_safety`** — deterministic SAFE/CONDITIONAL/CAUTION/NEVER_AUTO
  classification matching the knowledge base's documented guidance.
- **`clean_approved_items`** — the only function that deletes anything,
  defaults to `dry_run=True`, and only ever touches the exact paths passed
  in by the UI after explicit user approval.
- **`verify_cleanup`** — confirms post-deletion filesystem state rather
  than assuming success.

---

## 8. How Each Agent Satisfies the Rubric

| Criterion | CommandCheck | Storage Detective |
|---|---|---|
| Problem & Objective | Real, common developer problem: blindly pasted commands causing accidental data loss | Real, common end-user problem: "why is my disk full" with no visibility |
| Workflow & Tool Calling | 4 real tools (parser, heuristics, alternative lookup, verification) invoked by LangGraph nodes | 6 real tools (scan, classify, find_virtualenvs, clean, verify, human_size) invoked across 2 graphs |
| RAG / Embeddings | Chroma + MiniLM over 4 curated docs (git/linux/npm-pip/powershell), agent-decided retrieval | Chroma + MiniLM over storage-locations doc, retrieval per investigated category |
| LangGraph | 8-node graph with a genuine conditional edge | 2 graphs modeling a real human-approval gate |
| Output, Innovation & Demo | Playful, Gen-Z-toned verdict card UI with risk color coding, not a chatbot | "Crime scene" framing, per-item approval checkboxes, real before/after verification |

---

## 9. Filling Out the Evaluation Form

**Agent 1**
1. **Agent Name:** CommandCheck
2. **Problem Statement:** Developers/students paste terminal commands from AI tools or tutorials without understanding their effects, sometimes causing irreversible data loss.
3. **Objective/Purpose:** Act as a safety layer that explains, risk-rates, and (when needed) suggests safer alternatives for any terminal command before it's run.
4. **Target Users:** Students and developers who copy commands from ChatGPT/Claude/Stack Overflow/tutorials.
5. **Key Features:** Command parsing, intent understanding, effect analysis, RAG-grounded documentation lookup, deterministic + LLM risk assessment, safer-alternative suggestions, verification commands.
6. **Technologies Used:** Python, LangChain, LangGraph, Chroma, HuggingFace sentence-transformers, Streamlit.
7. **LLM / Model Used:** Claude (via `langchain-anthropic`), configurable to GPT-4o-mini.
8. **Tools / APIs Used:** `parse_command`, `assess_risk_heuristics`, `lookup_safer_alternative`, `suggest_verification` (custom Python tools).
9. **RAG / Vector Store Used:** Chroma, embedding model `sentence-transformers/all-MiniLM-L6-v2`, corpus = git/linux/npm-pip/powershell reference docs.
10. **Framework: LangChain / LangGraph Used:** Yes — both.
11. **Input:** A single terminal command pasted as text.
12. **Expected Output:** Risk verdict (SAFE→DESTRUCTIVE), plain-language explanation, effects breakdown, safer alternative (if any), verification command.
13. **GitHub / Project Link:** *(add after you push to GitHub)*
14. **Demo / Video Link:** *(record after deployment)*
15. **How is this Agent different from Agent 2?** CommandCheck is a pre-execution safety/explainer for arbitrary terminal commands; Storage Detective is a post-hoc filesystem investigator with a destructive-action approval workflow. Different inputs (text command vs. filesystem scan), different knowledge bases, different graph shapes (single linear+conditional graph vs. two graphs split by a human-approval gate).

**Agent 2**
- **Agent Name:** Storage Detective
- **Problem Statement:** Users see "X GB used" with no breakdown of what's actually consuming their disk, and are afraid to delete things that might be important.
- **Objective/Purpose:** Investigate storage usage like a forensic detective, explain what's safe to remove and why, and only clean up what the user explicitly approves.
- **Target Users:** Everyday laptop users and developers running low on disk space.
- **Key Features:** Real filesystem scanning, safety classification, RAG-grounded per-item explanations, prioritized cleanup list, mandatory per-item approval, verified deletion.
- **Technologies Used:** Python, LangChain, LangGraph, Chroma, HuggingFace sentence-transformers, Streamlit.
- **LLM / Model Used:** Claude (via `langchain-anthropic`), configurable to GPT-4o-mini.
- **Tools / APIs Used:** `scan_storage`, `find_virtualenvs`, `classify_safety`, `clean_approved_items`, `verify_cleanup` (custom Python tools operating on the real filesystem).
- **RAG / Vector Store Used:** Chroma, embedding model `sentence-transformers/all-MiniLM-L6-v2`, corpus = storage-locations safety reference doc.
- **Framework: LangChain / LangGraph Used:** Yes — both.
- **Input:** A "Scan My Storage" click (optionally a folder path to search for old virtual environments).
- **Expected Output:** Categorized storage breakdown with sizes, safety classification per category, grounded explanation, and (after approval) a cleanup + verification report.
- **GitHub / Project Link:** *(add after you push to GitHub)*
- **Demo / Video Link:** *(record after deployment)*
- **How is this Agent different from Agent 1?** Storage Detective analyzes and modifies the filesystem itself with a human-approval gate before any destructive action; CommandCheck never touches the filesystem at all — it only analyzes text input and returns a verdict.
