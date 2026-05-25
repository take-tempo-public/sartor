# Installing callback.

> **Purpose:** end-to-end install guide for users on Windows, macOS,
> or Linux. The minimum-friction path to a running app + first
> generated résumé.
> **Audience:** humans installing callback. for the first time.
> **Authoritative for:** OS-specific install steps, the Playwright
> Chromium download step, API-key setup, troubleshooting.
> Sibling docs:
> [`README.md`](../README.md) (overview),
> [`SECURITY.md`](../SECURITY.md) (what stays on your machine),
> [`docs/architecture.md`](architecture.md) (developer view).

---

## Prerequisites

- **Python 3.10 or newer.** Verify with `python --version` (or
  `python3 --version` on macOS/Linux).
- **An Anthropic API key.** Get one at
  [console.anthropic.com](https://console.anthropic.com/). The
  first generation is ~$0.05–$0.30 in API spend; budget guards
  documented in [`SECURITY.md`](../SECURITY.md).
- **~150 MB of free disk space** for the Chromium binary
  Playwright downloads for PDF rendering. The binary lives in
  your OS user cache (`%LOCALAPPDATA%\ms-playwright` on Windows,
  `~/.cache/ms-playwright` on Linux, `~/Library/Caches/ms-playwright`
  on macOS) — **outside** the repo, not committed.
- **A modern browser** (Chrome / Edge / Firefox / Safari).
  callback. runs as a local Flask app you access in your browser.

---

## Windows

1. **Install Python** from [python.org](https://www.python.org/downloads/).
   During install, check **"Add Python to PATH"**.

2. **Open a terminal** — press `Win + R`, type `cmd`, press Enter.

3. **Clone the repo and navigate into it:**
   ```cmd
   git clone https://github.com/amodal1/callback C:\Dev\callback
   cd C:\Dev\callback
   ```

4. **Install dependencies:**
   ```cmd
   pip install -e .
   ```

5. **Download the Chromium binary for PDF rendering** (one-time, ~150 MB):
   ```cmd
   python -m playwright install chromium
   ```

6. **Set your API key** (choose one):

   - **Environment variable (recommended):**
     ```cmd
     set ANTHROPIC_API_KEY=your-key-here
     ```
     Permanent: System Properties → Environment Variables.
   - **Key file:** create a file named `.api_key` in the repo
     root containing only your key.

7. **Run the app:**
   ```cmd
   python app.py
   ```

8. **Open your browser** and visit `http://localhost:5000`.

---

## macOS

1. **Install Python** (if not already):
   ```bash
   brew install python
   ```
   Or download from [python.org](https://www.python.org/downloads/).

2. **Open Terminal** — `Cmd + Space`, type `Terminal`, Enter.

3. **Clone and enter the repo:**
   ```bash
   git clone https://github.com/amodal1/callback ~/callback
   cd ~/callback
   ```

4. **Install dependencies:**
   ```bash
   pip3 install -e .
   ```

5. **Download Chromium for PDF rendering:**
   ```bash
   python3 -m playwright install chromium
   ```

6. **Set your API key:**
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```
   Permanent: add that line to `~/.zshrc` (or `~/.bash_profile`)
   and `source ~/.zshrc`.

   Or create a `.api_key` file in the repo root:
   ```bash
   echo "your-key-here" > .api_key
   ```

7. **Run the app:**
   ```bash
   python3 app.py
   ```

8. **Open your browser** to `http://localhost:5000`.

---

## Linux

1. **Install Python** (most distros include it; verify):
   ```bash
   python3 --version
   ```
   If missing:
   ```bash
   # Ubuntu / Debian
   sudo apt install python3 python3-pip
   # Fedora / RHEL
   sudo dnf install python3 python3-pip
   # Arch
   sudo pacman -S python python-pip
   ```

2. **Clone and enter the repo:**
   ```bash
   git clone https://github.com/amodal1/callback ~/callback
   cd ~/callback
   ```

3. **Install dependencies:**
   ```bash
   pip3 install -e .
   ```

4. **Download Chromium for PDF rendering:**
   ```bash
   python3 -m playwright install chromium
   ```
   On some distros Playwright also needs system libraries. If the
   `chromium install` command warns about missing deps, follow its
   on-screen instructions (usually one `apt install` line).

5. **Set your API key:**
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```
   Permanent: add to `~/.bashrc` or `~/.zshrc`.

6. **Run the app:**
   ```bash
   python3 app.py
   ```

7. **Open your browser** to `http://localhost:5000`.

---

## First-run walkthrough

After the app is running:

1. **Select or create a user** in the top-right user picker.
   Each user has their own corpus, settings, and output history.
2. **Open the Career Corpus tab** and click `+ IMPORT LEGACY` if
   you have an existing résumé file in `resumes/<user>/`. The
   importer extracts experiences and bullets into the structured
   corpus (uses one Haiku call, ~$0.02).
3. **Click the Application tab → Start application.**
4. Follow the six-step wizard:
   1. **Job description** — paste the JD text.
   2. **Clarify** *(optional)* — answer 3-5 LLM questions that
      surface real-but-undocumented experience.
   3. **Compose** — pin, exclude, or add bullets and pick which
      summary variant to use.
   4. **Template** — choose a layout; preview updates live.
   5. **Generate** — produce the résumé in DOCX, PDF, or Markdown.
   6. **Download** — review, refine, and download.
5. *(Optional)* Generate a cover letter against the finalized
   résumé using the **+ Generate cover letter** button.

Total cost per application: typically **$0.05–$0.30** in
Anthropic API spend (more if you iterate clarify + generate
several times).

---

## Troubleshooting

**"I just shipped a UI change but the browser still shows the
old version."**
The app sends `Cache-Control: no-cache` on the HTML shell and
`max-age=0` on `/static/*`, so this shouldn't happen in normal
use. If it does: clear the browser cache for `localhost:5000`
(DevTools → Network → "Disable cache" while DevTools is open,
then reload). One-time fix.

**"Generation fails with 'AI generation response was malformed
after retry.'"**
The LLM occasionally emits raw control characters in the JSON
response. The parser tolerates this since `2d7c564` (added
`strict=False`). If you still see this error on current `main`,
file an issue with the `detail:` line attached.

**"Chromium not found" when trying to generate PDF.**
Run `python -m playwright install chromium` again. The Chromium
binary lives in your OS user cache, not the repo, so a fresh
clone needs the install step.

**"API key not picked up."**
Confirm one of:
- `echo $ANTHROPIC_API_KEY` (or `echo %ANTHROPIC_API_KEY%` on
  Windows) shows your key in the same shell where you launched
  `python app.py`.
- `.api_key` exists in the repo root and contains only the key,
  no quotes, no trailing newline.

**Port 5000 already in use.**
Another process is on `:5000`. On Windows: `netstat -ano | findstr :5000`
to find the PID, then `taskkill /PID <pid> /F`. On macOS/Linux:
`lsof -i :5000` then `kill <pid>`. Or change the port in
[`app.py`](../app.py) `main()` — search for `port=5000`.

**"My data is somewhere I can't find."**
See the "What gets saved on your machine" section in
[`README.md`](../README.md). The short answer: `configs/`,
`resumes/`, `output/`, `db/resume.sqlite`, `logs/` — all under
the repo root.

---

## Verifying the install

After the steps above:

```bash
python -m pytest -q
```

Should report `627+ passed`. Then:

```bash
python -m ruff check .
```

Should report `All checks passed!`.

If either fails on a fresh clone, check the Python version and
re-run `pip install -e .` (a partial install can leave
dependencies out of sync).
