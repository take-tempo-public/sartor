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

    @staticmethod
    def step_button(step: int) -> str:
        return f"button.wizard-step[data-wstep='{step}']"


class PriorApps:
    PANEL = "#panelApplications"
    LIST = "#applicationsList"
    MODAL = "#appDetailModal"
    RESUME_BUTTON = "#btnResumeApp"

    @staticmethod
    def card(app_id: int) -> str:
        return f"#app-card-{app_id}"


class Personas:
    PANEL = "#panelPersonas"


class Memory:
    PANEL = "#panelMemory"


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
    are structural attributes the console JS depends on (tab routing + drawer
    population) — stable handles, not styling aliases."""

    ROOT = ".cb-dash"
    TABS = ".dash-tab"
    DRAWER = "#drawer"
    DRAWER_OPEN = "#drawer.open"
    DRAWER_CLOSE = "#drawerClose"
    DRAWER_BODY = "#drawerBody"
    DRAWER_TITLE = "#drawerTitle"

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
