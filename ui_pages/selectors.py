"""THE selector registry for the sartor. UI.

One place to edit on any reskin (the first-class redesign-resilience
requirement, decided 2026-06-04). Prefer stable IDs and ARIA roles. Where a
class is the only handle (`.corpus-card`, `.compose-experience-card`,
`.drag-handle`), it is a *structural* class the JS render path depends on,
not a styling alias — still centralized here so a rename is a one-file edit.

Verified against `templates/index.html` and the proven navigation in
`scripts/capture_screenshots.py`.
"""

from __future__ import annotations


class UserPicker:
    """Selectors for the landing user-picker panel."""

    PANEL = "#panelUser"
    SELECT = "#userSelect"
    NEW_USER_LINK = "text=New user"
    NEW_USER_FORM = "#newUserForm"
    NEW_USERNAME = "#newUsername"
    NEW_NAME = "#newName"
    NEW_EMAIL = "#newEmail"
    CREATE_BUTTON = "text=Create"
    CANCEL_BUTTON = "#newUserForm >> text=Cancel"
    # F-05 — display-name-first form: the username hint under the (now
    # secondary) username field, auto-derived as a slug from the full name.
    NEW_USERNAME_HINT = "#newUsernameHint"

    # Wave 2 recruiter tier (UX review F-08) — the searchable candidate roster
    # layered above SELECT. It sets SELECT's value; it never replaces it.
    ROSTER = "#candidateRoster"
    ROSTER_SEARCH = "#candidateRosterSearch"
    ROSTER_LIST = "#candidateRosterList"
    ROSTER_CARD = ".candidate-roster-card"

    @staticmethod
    def roster_card(username: str) -> str:
        """Return the roster-card selector for a given username."""
        return f"#roster-card-{username}"


class Forms:
    """Cross-surface form conventions (Sprint 6.3 #21).

    The required-field marker is a reusable class shared by the new-user form,
    the openFormModal modals, and the diagnostics dropdowns — one handle for
    all of them.
    """

    REQUIRED_MARKER = ".required-marker"
    REQUIRED_LEGEND = ".form-required-legend"


class Help:
    """Reusable in-app help primitive (Sprint 6.5 feat/help-pattern-component).

    ONE shared #helpModal whose title/body swap per block; a `.help-info`
    (i)-circle is injected into each registered `.cb-panel` header and re-opens
    that block's modal. The welcome block also auto-opens once-ever on first
    view (default-suppressed in the UX suite — see the `_help_welcome_default_seen`
    fixture + the `show_welcome` marker).
    """

    MODAL = "#helpModal"
    MODAL_TITLE = "#helpModalTitle"
    MODAL_BODY = "#helpModalBody"
    CLOSE = "#btnCloseHelp"
    BACKDROP = "#helpModal .cb-modal-backdrop"
    ICON = ".help-info"
    INLINE = ".help-inline"

    @staticmethod
    def icon(block_id: str) -> str:
        """The injected (i)-circle for a given block (e.g. ``panelUser``)."""
        return f"#help-icon-{block_id}"


class Header:
    """Top-bar wordmark (`.cb-wordmark`) — clicking it routes home (#23).

    Deselects the user and returns to the default Tailor landing tab.
    """

    TOPBAR = "#cbTopbar"
    WORDMARK = ".cb-wordmark"


class DemoMode:
    """F-19 offline/demo-mode banner (`SARTOR_DEMO=1`, `config.Config.demo_mode`).

    Persistent, always-visible at the very top of the page — never a
    dismissible toast — while demo mode is active.
    """

    BANNER = ".demo-mode-banner"


class ErrorModal:
    """The shared error modal (`reportError()` in app.js opens it).

    Every surfaced failure — including a download error (F-10: never a silent
    no-op) — lands here with a copyable stage/message/detail block.
    """

    MODAL = "#errorModal"
    TEXT = "#errorModalText"


class LiveRegion:
    """The shell's screen-reader announcer (`_announce()` in app.js).

    Writes here at every meaningful async completion — analysis ready, generation
    done, edits saved. A polite, atomic sr-only region; its content is assertable
    via `to_contain_text` (sr-only ≠ hidden for text assertions). F-expa11y-08.
    """

    ANNOUNCER = "#srAnnounce"


class TopTabs:
    """Selectors for the top-bar section tabs (Corpus/Tailor/Personas/Memory/Pipeline)."""

    CORPUS = "#topTabCorpus"
    TAILOR = "#topTabTailor"
    PERSONAS = "#topTabPersonas"
    MEMORY = "#topTabMemory"
    # Wave 2 recruiter tier (UX review F-17) — cross-candidate pipeline board.
    PIPELINE = "#topTabPipeline"


class Corpus:
    """Selectors for the Career Corpus tab."""

    PANEL = "#panelCorpus"
    EXPERIENCE_LIST = "#corpusExperienceList"
    CARD = "#corpusExperienceList .corpus-card"
    # Accessible-name (substring) match for the `+ Import résumé` button.
    IMPORT_BUTTON_NAME = "Import résumé"
    # β.6e summary-variants editor (#2 — the Add-variant affordance).
    SUMMARY_VARIANTS_SECTION = "#summaryVariantsSection"
    ADD_VARIANT_BUTTON_NAME = "Add variant"
    # KW2 — onboarding banner + corpus-wide accept-all control.
    ONBOARDING_BANNER = "#onboardingBanner"
    ACCEPT_ALL_BUTTON_NAME = "Accept all pending"
    # Sprint 6.4 (#16/#1) — review-finished hand-off CTA into the Tailor tab,
    # shown in the banner's ready state (non-empty corpus + 0 pending).
    START_TAILORING_BUTTON = "#btnStartTailoring"
    # B.4 (Sprint 6.6) — per-role intro variants editor inside an expanded
    # experience card (injected by _renderExperienceSummarySection).
    EXP_SUMMARY_SECTION = ".exp-summary-variants-section"
    ADD_INTRO_BUTTON_NAME = "Add intro"
    # F-04 (UX-W1, 2026-07-07) — Education + Certifications editors.
    EDUCATION_SECTION = "#educationEditorSection"
    EDUCATION_LIST = "#educationEditorList"
    ADD_EDUCATION_BUTTON_NAME = "Add education"
    CERTIFICATIONS_SECTION = "#certificationsEditorSection"
    CERTIFICATIONS_LIST = "#certificationsEditorList"
    ADD_CERTIFICATION_BUTTON_NAME = "Add certification"


class Wizard:
    """Selectors for the tailoring wizard (Steps 1-6) panels and controls."""

    RAIL = "#wizardRail"
    # "↻ Start new tailoring" — clears the current run back to Step 1 without a
    # browser refresh. Revealed alongside the rail once the wizard engages.
    RAIL_ACTIONS = "#wizardRailActions"
    NEW_TAILORING_BUTTON = "#btnNewTailoring"
    PANEL_ANALYSIS = "#panelAnalysis"
    JD_TEXT = "#jdText"
    ANALYZE_BUTTON = "#btnAnalyze"
    ANALYSIS_CONTENT = "#analysisContent"
    # F-12 — progressive disclosure: the verdict + top-3-actions block that
    # leads the render, and the <details> fold holding the deep analysis
    # (collapsed by default; open via its <summary>).
    ANALYSIS_VERDICT = "#analysisVerdict"
    ANALYSIS_DETAILS = "#analysisDetails"
    ANALYSIS_DETAILS_SUMMARY = "#analysisDetails > summary"
    # In-flow "Continue" buttons have no ids (onclick=wizardGoTo(n)); text is
    # the only handle. Centralized here so a copy edit is a one-file change.
    CONTINUE_TO_CLARIFY = "text=Continue to Clarify →"
    PANEL_CLARIFY = "#panelClarify"
    # The "Get clarifying questions / Skip" row — the manual entry kept for a
    # direct rail click into Step 2. "Continue to Clarify →" bypasses it
    # (finding #6), so it must be hidden on that path.
    CLARIFY_START_ROW = "#clarifyStartRow"
    CLARIFY_BUTTON = "#btnClarify"
    CLARIFY_QUESTIONS = "#clarifyQuestions"
    CLARIFY_QUESTION_TEXTAREA = "#clarifyQuestions textarea"
    SUBMIT_CLARIFICATIONS = "#btnSubmitClarifications"
    PANEL_COMPOSE = "#panelCompose"
    # "Skip to Compose →" on the analysis panel — fires recommend_bullets
    # before loading Compose (vs a bare rail click, which skips recommend).
    SKIP_TO_COMPOSE = "#btnSkipFromAnalysis"
    SAVE_CONTINUE_TEMPLATE = "text=Save and continue to Template →"
    PANEL_TEMPLATE = "#panelTemplate"
    TEMPLATE_OPTIONS = "#templatePickList [role='option']"
    LIVE_PREVIEW_FRAME = "#livePreviewFrame"
    CONTINUE_TO_GENERATE = "text=Continue to Generate →"
    PANEL_GENERATE = "#panelGenerate"
    GENERATE_BUTTON = "#btnGenerate"
    # F-09 — Step 5's state-aware copy pair (_renderGenerateStepCopy toggles
    # exactly one visible): FROZEN carries the deterministic-assembly claim
    # (only after Compose's Save-and-continue froze an approved_composition);
    # LEGACY keeps the original LLM-generate framing.
    GENERATE_COPY_LEGACY = "#generateStepCopyLegacy"
    GENERATE_COPY_FROZEN = "#generateStepCopyFrozen"
    REFINEMENT_INPUT = "#refinementInput"
    OUTPUT_PREVIEW_BLOCK = "#outputPreviewBlock"
    OUTPUT_PREVIEW_FRAME = "#outputPreviewFrame"
    # Post-generation "Follow-up clarification" controls (the iteration interview
    # the user triggers from the Output panel via #btnIterateClarify). The id is
    # stable across the KW8 copy rename — only the visible label changed.
    ITERATE_CLARIFY_BUTTON = "#btnIterateClarify"
    ITERATE_CLARIFY_AREA = "#iterateClarifyArea"
    ITERATE_CLARIFY_QUESTIONS = "#iterateClarifyQuestions"
    ITERATE_CLARIFY_QUESTION_TEXTAREA = "#iterateClarifyQuestions textarea"
    ITERATE_CLARIFY_DIVIDER_LABEL = "#iterateClarifyArea .clarify-divider-label"

    @staticmethod
    def step_button(step: int) -> str:
        """Return the rail-button selector for a wizard step."""
        return f"button.wizard-step[data-wstep='{step}']"


class PriorApps:
    """Selectors for the Prior Applications panel and detail modal."""

    PANEL = "#panelApplications"
    LIST = "#applicationsList"
    MODAL = "#appDetailModal"
    RESUME_BUTTON = "#btnResumeApp"
    # #24 — editable job-title / company inputs in the detail modal.
    TITLE_INPUT = "#appDetailTitle"
    COMPANY_INPUT = "#appDetailCompany"
    # #24 — the relabeled (was "N pending") proposal pill on a card.
    PENDING_PILL = ".application-card-pending"

    @staticmethod
    def card(app_id: int) -> str:
        """Return the card selector for an application id."""
        return f"#app-card-{app_id}"

    @staticmethod
    def card_company(app_id: int) -> str:
        """Return the company-field selector within an application card."""
        return f"#app-card-{app_id} .application-card-company"


class Personas:
    """Selectors for the Personas tab."""

    PANEL = "#panelPersonas"
    OWNED_GRID = "#personaOwnedGrid"
    # Wave 2 recruiter tier (UX review F-16) — the per-owned-card copy action
    # + its openFormModal candidate picker (shared #formModal, see Compose).
    COPY_BUTTON_NAME = "COPY TO CANDIDATE"
    COPY_TARGET_SELECT = "#formModal_username"

    @staticmethod
    def card(persona_id: int) -> str:
        """Return the card selector for a persona id."""
        return f"#persona-card-{persona_id}"


class Pipeline:
    """Selectors for the cross-candidate Pipeline tab (Wave 2 recruiter tier, F-17)."""

    PANEL = "#panelPipeline"
    BOARD = "#pipelineBoard"
    COLUMN = ".pipeline-column"
    ROW = ".pipeline-row"
    COUNT = "#pipelineCount"


class Memory:
    """Selectors for the Memory tab."""

    PANEL = "#panelMemory"


class Assistant:
    """The doc-grounded assistant (Sprint 7.5, feat/doc-assistant).

    Relocated from an in-shell collapsible `<details>` panel to a fixed top-bar
    magnifier pill (`#assistantPill`) that opens a floating `.cb-modal`
    (`#assistantModal`) via `openAssistantModal()`. Backed by POST
    /api/assistant/ask (SSE). JS in `static/assistant.js`.
    """

    OPEN_PILL = "#assistantPill"  # the top-bar magnifier that opens the modal
    MODAL = "#assistantModal"
    MODAL_TITLE = "#assistantModalTitle"
    CLOSE = "#btnCloseAssistant"
    BACKDROP = "#assistantModal .cb-modal-backdrop"
    DEV_MODE = "#assistantDevMode"
    QUESTION = "#assistantQuestion"
    ASK_BUTTON = "#assistantAsk"
    ANSWER = "#assistantAnswer"
    STATUS = "#assistantStatus"  # polite live region: "Thinking…" / "Answer ready."
    SOURCES = "#assistantSources"  # 7.8d: the numbered, resolving cited-only "Sources" key


class Settings:
    """The right-slide Settings drawer (Workstream B1.3).

    Opened from the header pill; profile/config fields live inside
    (`#cfgName` … `#cfgNotes`).
    """

    OPEN_PILL = "#settingsPill"
    DRAWER = "#settingsDrawer"
    LINKEDIN_INPUT = "#cfgLinkedin"
    # PX-02 — opt-in profile/website/portfolio scrape trigger + its status line.
    FETCH_PROFILE_BTN = "#btnFetchProfile"
    FETCH_PROFILE_STATUS = "#profileFetchStatus"
    # F-03/F-04 (UX-W1, 2026-07-07) — the live-field / corpus-pointer row pair
    # per flat field; exactly one of each pair is visible at a time.
    SKILLS_FIELD_ROW = "#cfgSkillsFieldRow"
    SKILLS_CORPUS_ROW = "#cfgSkillsCorpusRow"
    CERTS_FIELD_ROW = "#cfgCertsFieldRow"
    CERTS_CORPUS_ROW = "#cfgCertsCorpusRow"
    EDUCATION_FIELD_ROW = "#cfgEducationFieldRow"
    EDUCATION_CORPUS_ROW = "#cfgEducationCorpusRow"
    GO_TO_CORPUS_BUTTON_NAME = "Go to Career corpus"


class Onboarding:
    """The shared empty-corpus CTA (`_renderCorpusEmptyCTA`).

    Rendered into a read-only tab (Memory / Personas / Applications) when the
    selected user has no corpus material yet. The Corpus tab itself shows its
    toolbar instead (see Corpus.IMPORT_BUTTON_NAME), so both import and manual
    CRUD are open.
    """

    CTA_NAME = "Go to Career corpus"


class Output:
    """Selectors for the Step-6 output panel (preview + downloads)."""

    PANEL = "#panelOutput"
    PREVIEW_BLOCK = "#outputPreviewBlock"
    PREVIEW_FRAME = "#outputPreviewFrame"
    DOWNLOAD_RESUME = "#btnDownloadResume"
    DOWNLOAD_COVER = "#btnDownloadCover"
    GENERATE_COVER = "#btnGenerateCover"
    COVER_TAB = "#tabBtnCoverLetter"
    COVER_TAB_ACTIVE = "#tabCoverLetter.active"
    COVER_PREVIEW = "#coverLetterPreview, #tabCoverLetter [contenteditable]"


class Dashboard:
    """The /_dashboard diagnostics console.

    data-tab / data-pane / data-detail are structural attributes the console JS
    depends on (tab routing + detail-panel population) — stable handles, not
    styling aliases.
    """

    ROOT = ".cb-dash"
    TABS = ".dash-tab"
    # The detail surface is a full-width inline panel (was a side drawer); it's
    # closed via the `hidden` attribute, so "open" = `:not([hidden])`.
    DETAIL_PANEL = "#detailPanel"
    DETAIL_PANEL_OPEN = "#detailPanel:not([hidden])"
    DETAIL_CLOSE = "#detailClose"
    DETAIL_BODY = "#detailBody"
    DETAIL_TITLE = "#detailTitle"

    @staticmethod
    def tab(name: str) -> str:
        """Return the selector for a dashboard tab by name."""
        return f".dash-tab[data-tab='{name}']"

    @staticmethod
    def pane(name: str) -> str:
        """Return the selector for a dashboard pane by name."""
        return f".dash-pane[data-pane='{name}']"

    @staticmethod
    def pane_active(name: str) -> str:
        """Return the active-pane selector for a dashboard pane by name."""
        return f".dash-pane[data-pane='{name}'].active"

    @staticmethod
    def tile(detail: str) -> str:
        """Return the tile selector bound to a detail block."""
        return f".tile[data-detail='{detail}']"

    # --- per-tab education (Sprint 6.5 feat/education-diagnostics-annotate) ---
    # Each pane opens with a one-line summary + an (i) that opens its explainer
    # modal. The (i) and #helpModal reuse the wizard's `.help-info`/`#helpModal`
    # ids, so the shared `Help` selector class applies on the dashboard too.
    PANE_INTRO = ".dash-pane-intro"

    # --- Annotate tab (the console's read-write surface) ---
    # Stable ids the annotate IIFE binds to (load/save/collate + bootstrap wrapper).
    ANN_FIXTURE_SELECT = "#fixtureSelect"
    ANN_FIXTURE_RELOAD = "#fixtureReload"
    ANN_FIXTURE_EMPTY = "#fixtureEmpty"
    ANN_EDITOR = "#annEditor"
    ANN_META = "#annMeta"
    ANN_ERROR = "#annError"
    ANN_BULLETS = "#annBullets"
    ANN_SKILLS = "#annSkills"
    ANN_CLAR = "#annClar"
    ANN_ITEM = ".ann-item"
    ANN_SAVE = "#annSave"
    ANN_COLLATE = "#annCollate"
    ANN_STATUS = "#annStatus"
    # Bootstrap-wrapper sub-panel.
    ANN_BOOTSTRAP_SECTION = "#bootstrapSection"
    ANN_BS_USER = "#bsUser"
    ANN_BS_SLUG = "#bsSlug"
    ANN_BS_ADD_JD = "#bsAddJd"
    ANN_BS_RUN = "#bsRun"
    ANN_BS_PROGRESS = "#bsProgress"
    # Tuning tab — "Real-corpus seed (optional)" sub-panel. #bsUser + #tuneUser
    # are <select data-user-source> auto-populated from /api/users (Sprint 6.3
    # #20-dropdown); both opt in via the data attribute.
    USER_SOURCE_SELECT = "select[data-user-source]"
    TUNE_USER = "#tuneUser"
    TUNE_SLUG = "#tuneSlug"


class Compose:
    """Selectors for the Step-3 compose surface (bullets, titles, role intros)."""

    LIST = "#composeList"
    EXPERIENCE_CARD = "#composeList .compose-experience-card"
    # The visible (résumé-bound) bullet container; carries data-exp-id and
    # data-custom-order. Drag/keyboard reorder + order serialization are
    # scoped to this set (drawer rows excluded).
    BULLET_LIST = ".compose-bullet-list"
    ROW = ".compose-row"
    # A recommended bullet row only exists after the post-recommend render —
    # the deterministic "final render done" signal on the skip-to-compose
    # path (which loadComposition-renders twice: before + after recommend).
    RECOMMENDED_ROW = ".compose-bullet-list > .compose-row.recommended"
    ROW_TEXT = ".row-text"
    DRAG_HANDLE = ".drag-handle"
    DRAGGABLE = ".draggable"
    RESET_ORDER = ".compose-order-reset"
    MOVE_UP_LABEL = "Move bullet up"
    MOVE_DOWN_LABEL = "Move bullet down"
    # feat/compose-add-title — per-JD title selection + the add affordance.
    TITLE_LIST = ".compose-title-list"
    TITLE_RADIO = ".compose-title-radio"
    ADD_TITLE_BTN = ".compose-add-title-btn"
    # openFormModal field input + submit (shared add-title / add-bullet modal).
    FORM_MODAL_TITLE_INPUT = "#formModal_title"
    FORM_MODAL_SUBMIT = "#formModalSubmit"
    # β.6c — candidate-level positioning (summary) card variants on compose.
    POSITIONING_VARIANT = ".positioning-variant"
    POSITIONING_CHOSEN = ".positioning-variant.positioning-chosen"
    # Generation-experience re-architecture — the Compose-drafted 2-sentence
    # positioning summary (editable) + its Regenerate/Retire actions.
    POSITIONING_DRAFT = "#composeSummaryDraft"
    POSITIONING_DRAFT_REGEN = ".positioning-draft-regen"
    POSITIONING_DRAFT_RETIRE = ".positioning-draft-retire"
    # Phase 3 — per-role "Suggested for this JD" gap-fill lane (Accept/Retire).
    GAP_FILL_LANE = ".gap-fill-lane"
    GAP_FILL_ROW = ".gap-fill-row"
    GAP_FILL_ACCEPT = ".gap-fill-accept"
    GAP_FILL_RETIRE = ".gap-fill-retire"
    # B.4 (Sprint 6.6) — "Add role intros" opt-in toggle + the per-role intro
    # picker rendered inside each compose card.
    ROLE_INTROS_TOGGLE = "#composeRoleIntrosToggle"
    ROLE_INTRO = ".compose-role-intro"
    ROLE_INTRO_VARIANT = ".role-intro-variant"
    ROLE_INTRO_CHOSEN = ".role-intro-variant.role-intro-chosen"
    # add-intro modal text field (openFormModal id = #formModal_<fieldname>).
    FORM_MODAL_TEXT_INPUT = "#formModal_text"
    # B.5 (Sprint 6.6) — candidate-level Skills card on the compose surface.
    SKILLS_CARD = "#composeList .skills-card"
    SKILL_ROW = ".compose-skill-row"
    SKILL_DROP = ".skill-drop"
    # Settle signal: loadComposition() (static/app.js) clears this on #composeList
    # at entry (before its fetch) and sets it after the final synchronous append,
    # so a *stably present* marker proves the auto-recommend re-render cascade
    # reached its terminal render. Consumed by WizardComposePage._wait_settled —
    # the deterministic fix for the Compose flaky-test class.
    READY = "#composeList[data-compose-ready]"
    # Terminal-render gate: READY present AND no background reload in flight.
    # `data-compose-bg-pending` is a counter attribute app.js sets while any
    # reload-firing background call (auto-cascade draft/recommend + user-action
    # pin/accept/add) is in flight and removes when it drains to zero. The
    # increment lands before loadComposition re-sets data-compose-ready, so the
    # ONLY (READY present + bg-pending absent) state is the true terminal render —
    # making this a deterministic settle signal (no timing heuristic). Consumed by
    # WizardComposePage._wait_settled.
    SETTLED = "#composeList[data-compose-ready]:not([data-compose-bg-pending])"
