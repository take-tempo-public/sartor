"""THE selector registry for the callback. UI.

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
    PANEL = "#panelUser"
    SELECT = "#userSelect"
    NEW_USER_LINK = "text=New user"
    NEW_USER_FORM = "#newUserForm"
    NEW_USERNAME = "#newUsername"
    NEW_NAME = "#newName"
    NEW_EMAIL = "#newEmail"
    CREATE_BUTTON = "text=Create"


class Forms:
    """Cross-surface form conventions (Sprint 6.3 #21). The required-field
    marker is a reusable class shared by the new-user form, the openFormModal
    modals, and the diagnostics dropdowns — one handle for all of them."""

    REQUIRED_MARKER = ".required-marker"
    REQUIRED_LEGEND = ".form-required-legend"


class Header:
    """Top-bar wordmark (`.cb-wordmark`) — clicking it routes home (#23):
    deselects the user and returns to the default Tailor landing tab."""

    TOPBAR = "#cbTopbar"
    WORDMARK = ".cb-wordmark"


class TopTabs:
    CORPUS = "#topTabCorpus"
    TAILOR = "#topTabTailor"
    PERSONAS = "#topTabPersonas"
    MEMORY = "#topTabMemory"


class Corpus:
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


class Wizard:
    RAIL = "#wizardRail"
    PANEL_ANALYSIS = "#panelAnalysis"
    JD_TEXT = "#jdText"
    ANALYZE_BUTTON = "#btnAnalyze"
    ANALYSIS_CONTENT = "#analysisContent"
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
        return f"button.wizard-step[data-wstep='{step}']"


class PriorApps:
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
        return f"#app-card-{app_id}"

    @staticmethod
    def card_company(app_id: int) -> str:
        return f"#app-card-{app_id} .application-card-company"


class Personas:
    PANEL = "#panelPersonas"


class Memory:
    PANEL = "#panelMemory"


class Settings:
    """The right-slide Settings drawer (Workstream B1.3) — opened from the
    header pill; profile/config fields live inside (`#cfgName` … `#cfgNotes`)."""

    OPEN_PILL = "#settingsPill"
    DRAWER = "#settingsDrawer"


class Onboarding:
    """The shared empty-corpus CTA (`_renderCorpusEmptyCTA`) rendered into a
    read-only tab (Memory / Personas / Applications) when the selected user has
    no corpus material yet. The Corpus tab itself shows its toolbar instead
    (see Corpus.IMPORT_BUTTON_NAME), so both import and manual CRUD are open."""

    CTA_NAME = "Go to Career corpus"


class Output:
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
    """The /_dashboard diagnostics console. data-tab / data-pane / data-detail
    are structural attributes the console JS depends on (tab routing +
    detail-panel population) — stable handles, not styling aliases."""

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
        return f".dash-tab[data-tab='{name}']"

    @staticmethod
    def pane(name: str) -> str:
        return f".dash-pane[data-pane='{name}']"

    @staticmethod
    def pane_active(name: str) -> str:
        return f".dash-pane[data-pane='{name}'].active"

    @staticmethod
    def tile(detail: str) -> str:
        return f".tile[data-detail='{detail}']"

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
