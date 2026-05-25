# Resume Optimizer

A local web application that tailors resumes and cover letters to specific job descriptions using the Claude AI API. Built on the [10 Principles](https://jdforsythe.github.io/10-principles/overview/) — deterministic Python tools handle all mechanical work; the LLM handles analysis and writing.

**LCARS-styled interface. Runs locally. No data leaves your machine except API calls to Anthropic.**

> **Doc map:** [`vision.md`](vision.md) (product intent) ·
> [`docs/PRODUCT_SHAPE.md`](docs/PRODUCT_SHAPE.md) (architecture) ·
> [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) (release gates) ·
> [`CLAUDE.md`](CLAUDE.md) (contributor contract) ·
> [`CONTRIBUTING.md`](CONTRIBUTING.md) (PR workflow) ·
> [`SECURITY.md`](SECURITY.md) (threat model).
> Each doc opens with a `Purpose / Audience / Authoritative for` block.

---

## Workflow

```
Select User → Upload Resume → Paste Job Description → Review Analysis → Download Tailored Resume + Cover Letter
```

Two explicit review gates before any output is generated or downloaded — you see what the AI found and what it wrote before committing.

---

## Requirements

- Python 3.10 or higher
- An [Anthropic API key](https://console.anthropic.com/)
- Internet connection (for API calls and optional LinkedIn/portfolio scraping)

---

## Installation

### Windows

1. **Install Python** (if not already installed)
   Download from [python.org](https://www.python.org/downloads/). During install, check **"Add Python to PATH"**.

2. **Open a terminal** — press `Win + R`, type `cmd`, press Enter.

3. **Navigate to the project folder:**
   ```cmd
   cd C:\Dev\resume
   ```

4. **Install dependencies:**
   ```cmd
   pip install -e .
   ```

5. **Set your API key** (choose one method):

   *Option A — Environment variable (recommended):*
   ```cmd
   set ANTHROPIC_API_KEY=your-key-here
   ```
   To make it permanent, add it via **System Properties → Environment Variables**.

   *Option B — Key file:*
   Create a file named `.api_key` in the project folder containing only your API key.

6. **Run the app:**
   ```cmd
   python app.py
   ```

7. **Open your browser** and go to: `http://localhost:5000`

---

### macOS

1. **Install Python** (if not already installed)
   Download from [python.org](https://www.python.org/downloads/) or use Homebrew:
   ```bash
   brew install python
   ```

2. **Open Terminal** — press `Cmd + Space`, type `Terminal`, press Enter.

3. **Navigate to the project folder:**
   ```bash
   cd /path/to/resume
   ```

4. **Install dependencies:**
   ```bash
   pip3 install -e .
   ```
   > If you have multiple Python versions, use `pip3` or `python3 -m pip`.

5. **Set your API key** (choose one method):

   *Option A — Environment variable (recommended):*
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```
   To make it permanent, add that line to your `~/.zshrc` (or `~/.bash_profile`) and run `source ~/.zshrc`.

   *Option B — Key file:*
   ```bash
   echo "your-key-here" > .api_key
   ```

6. **Run the app:**
   ```bash
   python3 app.py
   ```

7. **Open your browser** and go to: `http://localhost:5000`

---

### Linux

1. **Install Python** (most distros include it; verify version):
   ```bash
   python3 --version
   ```
   If needed, install via your package manager:
   ```bash
   # Ubuntu / Debian
   sudo apt install python3 python3-pip

   # Fedora / RHEL
   sudo dnf install python3 python3-pip

   # Arch
   sudo pacman -S python python-pip
   ```

2. **Navigate to the project folder:**
   ```bash
   cd /path/to/resume
   ```

3. **Install dependencies:**
   ```bash
   pip3 install -e .
   ```
   > On some systems: `python3 -m pip install -r requirements.txt`

4. **Set your API key** (choose one method):

   *Option A — Environment variable (recommended):*
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```
   To persist, add to `~/.bashrc` or `~/.zshrc`.

   *Option B — Key file:*
   ```bash
   echo "your-key-here" > .api_key
   ```

5. **Run the app:**
   ```bash
   python3 app.py
   ```

6. **Open your browser** and go to: `http://localhost:5000`

---

## Getting an API Key

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign in or create an account
3. Navigate to **API Keys** and click **Create Key**
4. Copy the key — you won't be able to see it again

---

## Using the App

### 1 — Select or Create a User

Each person using the app has their own profile stored in `configs/{username}.config`. Select an existing user from the dropdown, or click **NEW USER** to create one.

### 2 — Fill in Your Configuration

After selecting a user, the configuration panel appears. Fill in:
- Name, email, phone
- LinkedIn URL and/or website (optional — the app will fetch and include this content for richer analysis)
- Skills and certifications
- Education summary
- Any additional notes for the AI (e.g. "I prefer remote roles" or "targeting senior-level positions")

Click **SAVE CONFIG** when done.

### 3 — Upload a Resume

Drop a resume file onto the upload zone or click to browse. Supported formats:
- **Word** (`.docx`) — recommended; output will match this format
- **PDF** (`.pdf`) — readable; output will be `.docx`
- **Markdown** (`.md`) — output will be `.md`

Uploaded resumes are saved to `resumes/{username}/` and listed as chips below the upload zone.

### 4 — Paste the Job Description

Paste the full text of the job posting into the **JOB DESCRIPTION** panel. Select which resume to use from the dropdown. Click **ANALYZE**.

> This makes one API call to Claude. Analysis typically takes 15–30 seconds.

### 5 — Review the Analysis *(Human Gate #1)*

Before anything is generated, you see:
- **Keyword match score** — how well your resume matches the JD vocabulary
- **ATS warnings** — formatting issues that could hurt automated screening
- **Essential and preferred skills** identified in the JD
- **Hidden qualities** the role is looking for
- **Keyword gaps** — what's missing and where to add it
- **Suggestions** — specific, reasoned improvements per resume section
- **Overall positioning strategy**

Review this. If the JD was wrong or you want to try a different resume, adjust and re-run. When satisfied, click **GENERATE DOCUMENTS**.

### 6 — Review the Output *(Human Gate #2)*

The tailored resume and cover letter appear in-browser before you download anything. Use the tabs to review:
- **RESUME** — complete tailored resume text
- **COVER LETTER** — field-appropriate cover letter (3 paragraphs, 250-320 words, VP-level voice)
- **CHANGES** — list of what was modified and any proofreading notes

When satisfied, click **DOWNLOAD RESUME** and **DOWNLOAD COVER LETTER**. Files are saved to `output/{username}/` with timestamps.

---

## File Structure

```
resume/
├── app.py              # Web server and API routes
├── analyzer.py         # Claude API calls (analysis + generation)
├── parser.py           # Resume parsing (docx, pdf, markdown)
├── hardening.py        # Deterministic tools (keyword extraction, ATS checks)
├── generator.py        # Document generation (docx, markdown)
├── scraper.py          # URL content fetcher (LinkedIn, portfolio)
├── pyproject.toml      # Python dependencies + tooling config
├── .api_key            # Your API key (create this; not included)
├── configs/            # User configuration files
│   └── {username}.config
├── resumes/            # Uploaded resumes
│   └── {username}/
├── output/             # Generated documents and analysis context
│   └── {username}/
│       ├── context_{timestamp}.json   # Saved analysis (reusable)
│       ├── resume_{timestamp}.docx
│       └── cover_letter_{timestamp}.docx
├── templates/
│   └── index.html      # Single-page UI
└── static/
    ├── style.css        # LCARS theme
    └── app.js           # Frontend logic
```

---

## User Config Format

Each user's config is a plain JSON file at `configs/{username}.config`:

```json
{
  "name": "Your Name",
  "email": "you@example.com",
  "phone": "555-0100",
  "linkedin_url": "https://linkedin.com/in/yourhandle",
  "website_url": "https://yoursite.com",
  "portfolio_urls": [],
  "skills": ["Python", "Leadership", "Data Analysis"],
  "certifications": ["AWS Solutions Architect"],
  "education_summary": "BS Computer Science, University of X, 2015",
  "notes": "Targeting senior-level remote roles. Prefer mission-driven companies.",
  "latest_resume": "my_resume.docx"
}
```

You can edit this file directly or use the Config panel in the UI.

---

## Troubleshooting

**`ModuleNotFoundError`** — Run `pip install -e .` (or `pip3 install -e .` on Mac/Linux). For development tooling, install with extras: `pip install -e ".[dev]"`.

**`anthropic.AuthenticationError`** — Check your API key is set correctly. Try: `echo $ANTHROPIC_API_KEY` (Mac/Linux) or `echo %ANTHROPIC_API_KEY%` (Windows).

**Port 5000 already in use** — Change the port in `app.py` (last line): `app.run(debug=True, port=5001)`.

**PDF output is `.docx`** — PDF writing is complex; the app outputs `.docx` for PDF inputs. Open in Word or Google Docs.

**LinkedIn URL returns empty** — LinkedIn blocks most scrapers. Add your key experience to the **Notes** field in your config as a workaround.

**Slow analysis** — This is normal; the API call processes your full resume and JD. First run usually takes 20–40 seconds.

---

## Privacy

- Your resume and job description are sent to Anthropic's Claude API for analysis. Anthropic's [privacy policy](https://www.anthropic.com/privacy) applies.
- No data is stored externally. All files (resumes, configs, outputs) are on your local machine.
- The `.api_key` file is excluded from sharing by default — do not commit it to git.

---

## Architecture Notes

Built on the [Hardening Principle](https://jdforsythe.github.io/10-principles/principles/hardening/): deterministic Python code handles all mechanical work (file parsing, keyword counting, ATS checks, document generation). The LLM is called exactly twice per run — once for analysis, once for generation — with a structured context payload that targets 15-40% of the context window (Context Hygiene Principle). The analysis is saved to disk as a versioned JSON artifact (Disposable Blueprint Principle), enabling re-generation without re-analysis.

---

## Claude Code Plugin

The project ships a Claude Code plugin under [.claude-plugin/](.claude-plugin/) — slash commands, subagents, and hooks that automate the dev workflow. Activation via `.claude/settings.json` (no install step required).

### Commands

| Command | What it does |
|---|---|
| [`/eval`](.claude-plugin/commands/eval.md) | Run the eval harness against synthetic or real fixtures |
| [`/replay`](.claude-plugin/commands/replay.md) | Re-run `generate()` on a saved `context_*.json` |
| [`/prompt-tune`](.claude-plugin/commands/prompt-tune.md) | A/B test a `SYSTEM_PROMPT` edit against the eval suite |
| [`/bench`](.claude-plugin/commands/bench.md) | Aggregate `logs/llm_calls.jsonl` for cache hit rate, latency, cost |
| [`/inspect-context`](.claude-plugin/commands/inspect-context.md) | Pretty-print + schema-validate a saved `context_set` |

### Subagents

| Agent | When to invoke |
|---|---|
| [`eval-judge`](.claude-plugin/agents/eval-judge.md) | Grade one (artifact × rubric) → JSON verdict |
| [`prompt-archaeologist`](.claude-plugin/agents/prompt-archaeologist.md) | Trace an eval failure to a prompt rule and propose a unified-diff fix |
| [`git-flow`](.claude-plugin/agents/git-flow.md) | Execute git workflow under the project's conventions |

### Hooks

Deterministic gates that fire automatically on tool use. See [.claude-plugin/hooks/](.claude-plugin/hooks/):

- `block-secrets` — blocks API keys + writes to `.api_key`/`.env*`/`*.pem`/`*.key`
- `ruff-changed` — runs `ruff check` on staged Python before `git commit`
- `block-merge-to-main` — blocks merge/push to main without explicit `CLAUDE_CONFIRM_MERGE=1`
- `validate-context` — JSON-syntax + schema check on `output/**/context_*.json` writes
- `route-security-lint` — requires `_safe_username` + `_within` on new Flask routes
- `check-plan-approved` / `mark-plan-approved` / `cleanup-plan-on-merge` — plan-mode workflow

### Dashboard

While the app is running, navigate to [http://localhost:5000/_dashboard](http://localhost:5000/_dashboard) for a read-only view of LLM telemetry: per-call token counts, latency, cache hit ratio, and the eval-harness verdicts. Localhost-only.
