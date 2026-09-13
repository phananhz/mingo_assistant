# Min Assistant - Architecture and Refactor Audit

Audit date: 2026-09-12

## Scope and baseline

- Local checkout and origin/main were identical before refactoring:
  36800ba94356610b99c31b546ad1c54c073e1541.
- Initial working tree contained only the user-owned, untracked
  TemplatesBefore/ directory. It has not been modified.
- Python baseline: 3.12.10.
- Baseline compile check passed.
- Baseline unit tests: 111 passed.
- Baseline PyInstaller one-file build passed with
  packaging/pyinstaller/MingoAssistantQRMaxV3.spec.
- Baseline executable startup smoke test passed. The generated executable was
  dist/baseline/MinAssistant.exe (244,903,782 bytes).
- The build emitted warnings for optional modules such as pytest, onnx, and
  cv2.gapi; none caused the baseline build or startup smoke test to fail.

## Runtime and resource map

    mingo_assistant.__main__
      -> app.main
         -> AppPaths
         -> AppContainer
            -> repositories
            -> registration services
            -> administrative matcher
            -> QR readers/parser
            -> document services
         -> MainWindow
            -> workspace views

Source mode resolves resources from the project root. Frozen mode resolves
resources from PyInstaller's _MEIPASS. The canonical spec bundles the
administrative-place data, business-line data, QR models, Word templates,
branding, icons, and required native/runtime dependencies. No online resource
loading was introduced.

## Responsibility and dependency findings

| Area | Current responsibility/risk | Required behavior boundary |
| --- | --- | --- |
| MainWindow | Shell/navigation plus case lifecycle, profile orchestration, settings, and dependency creation | Navigation, case behavior, and the three fixed authorized-person profiles |
| BusinessRegistrationWorkspace | View, widget state, QR workflow, mapping, validation, save/export coordination, and formatting | Visible UI, identity synchronization, validation messages, and saved form_values |
| docx_generator.py | Template discovery, placeholder mapping, formatting, XML/table mutation, and package-specific rules | Exact template structure, protected regions, tables, fonts, bookmarks, checkboxes, page breaks, signatures |
| JSON repositories | Persistence shape leaked toward UI; legacy case payload was an unversioned list | Existing case files must load without data loss |
| Service construction | Services and repositories were created in multiple UI locations | Source and frozen resource paths must remain equivalent |
| Administrative data | A canonical asset/matcher exists, while aliases and normalization rules are still spread across parsers/document code | Existing post-merger address behavior |
| QR layer | OcrService name is broader than its dominant QR-scanning responsibility and contains fallback reader orchestration | Offline scanning and all packaged reader fallbacks |

No confirmed circular import was found during the baseline import/compile
inspection. The principal issue is high coupling and low cohesion rather than a
known import cycle.

## Highest regression risks

1. DOCX XML and layout mutations.
2. Identity-scoped synchronization when a recognized CCCD is edited.
3. Administrative-address matching and post-merger aliases.
4. Frozen resource discovery and QR native dependencies.
5. Backward-compatible loading of local JSON.
6. Export version folders and existing case metadata.

These areas should remain behavior-locked by regression tests while
responsibilities are moved incrementally.

## Security audit

- No API key, password, token, credential, or private-key pattern was found in
  the source scan.
- Real personal data existed as three hard-coded authorized-person profiles in
  MainWindow and was duplicated in tests.
- Product decision: these three profiles are mandatory built-in app data. They
  now live in the versioned bundled asset
  assets/defaults/authorized_person_profiles.json, are loaded through a
  repository, remain visible in the app, and cannot be deleted through the
  existing UI.
- Automated-test copies of those profiles were replaced with clearly fake
  identities, phone numbers, and reserved example email domains.
- Exact values from the mandatory profiles already occur in multiple historical
  Git commits. Git history was not rewritten.
- Word templates contain sample contact and identity-like values. They were not
  modified because template content and layout are protected behavior.
- Registration-office data contains public office phone numbers and is not
  classified as customer PII.

## Completed refactor phases

### Phase 1 - Security cleanup

- Removed mandatory profile values from UI source.
- Added a bundled, versioned defaults asset and repository.
- Retained the three fixed profiles as required product data.
- Replaced duplicated real-person test fixtures with fake test data.
- Preserved existing templates and Git history.

### Phase 2 - Foundation

- Added AppContainer as the process composition root.
- Shared the administrative matcher/address parser across relevant services.
- Injected case/profile/registration dependencies into MainWindow.
- Added a case repository protocol and case use-case facade.
- Added typed core data errors.
- Added schema version 1 for case JSON while retaining legacy-list reads.
- A malformed/unknown case JSON shape raises CorruptDataError and is not
  overwritten by the read path.

### Phase 3 - Domain

- Added UI-independent business-registration models for people, addresses,
  companies, business lines, capital contributions, organization owners,
  authorized people, and registration cases.
- Added a compatibility projection from legacy form_values; the stored payload
  remains unchanged.
- Monetary domain values use integer VND/Decimal, never float.
- Moved required-field and business-line validation out of the PySide widget.
- Added typed validation results with separate error/warning channels.

Phase 3 verification:

- compileall passed;
- 124 unit tests passed;
- source startup smoke test passed using an isolated temporary AppData folder;
- PyInstaller one-file build passed;
- the EXE archive contains assets/defaults/authorized_person_profiles.json;
- the Phase 3 executable remained running after the 15-second startup window;
- artifact: dist/phase3/MinAssistant.exe, 244,917,575 bytes,
  SHA-256 b5a5b2b85ccca19765211561f267b491cf2f3804adf2d1ac8b3bd8c30e6a40fb.

The smoke-test harness required explicit process cleanup because a one-file
child process retained the redirected pipe after the launcher was terminated.
The verified Phase 3 process was stopped; this was a harness cleanup issue, not
an application startup failure.

### Phase 4 - Registration workspace boundaries

- Added a per-workspace RegistrationViewModel for copied form state, typed
  domain projection, and validation.
- Moved export folder/version planning to RegistrationExportPlanner.
- Moved VND parsing, formatting, and Vietnamese number wording to a pure domain
  formatter.
- Preserved the existing workspace method surface as delegates so signals,
  previews, save behavior, and regression tests remain compatible.

### Phase 5 - MainWindow application boundaries

- Added AuthorizedPersonUseCases and injected it from AppContainer.
- MainWindow no longer reads/writes authorized-person persistence directly.
- Kept the existing profile manager page and compatibility methods, including
  legacy tests that construct MainWindow without its normal constructor.

### Phase 6 - DOCX boundaries

- Added a shared cached TemplateManifest reader.
- Added a business-registration TemplateRepository for owner-specific template
  selection.
- Added an atomic DocxPackageEditor for ZIP/XML package traversal and rewrite.
- Both business-registration and dependent-unit generation use the extracted
  manifest boundary.
- Existing placeholder resolution, XML mutations, tables, fonts, bookmarks,
  page breaks, checkbox behavior, signatures, and protected regions were not
  rewritten.

### Phase 7 - Persistence and local security

- Malformed JSON is copied beside the original as a timestamped
  .corrupt-*.bak file before a typed CorruptDataError is raised.
- The original malformed file is not deleted or overwritten.
- Corrupt case data produces a blocking user-facing startup error; corrupt local
  authorized profiles fall back to the three fixed profiles and show a warning.
- Added an opt-in Windows DPAPI JSON adapter with atomic writes and no hard-coded
  encryption key. It is not automatically enabled for existing plaintext files;
  a future explicit migration can use this boundary without data loss.
- Added a per-user QLockFile single-instance guard to prevent concurrent JSON
  writes from two application processes.

### Phase 8 - Engineering and integration

- Added a Python 3.12 Ruff configuration restricted to correctness/fatal errors.
  A full style run identified 188 pre-existing style/debt findings, so no broad
  auto-fix was applied.
- Removed one proven unreachable and unreferenced MRZ method.
- Added Windows GitHub Actions checks for compile, Ruff, unit tests, and
  integration tests.
- Added Dependabot configuration for pip and GitHub Actions.
- Added an integration workflow using fake data:
  create case -> save -> reload -> validate -> generate five real-template DOCX
  files.
- Added a fake QR -> CCCD parse -> administrative normalization integration
  test.

Phase 4-8 verification:

- compileall passed;
- Ruff correctness lint passed;
- 135 unit tests passed;
- 2 integration tests passed;
- DOCX boundary regression tests passed;
- no runtime/server/cloud dependency was added.

## Remaining technical debt

- BusinessRegistrationWorkspace and DocxTemplateGenerator are materially smaller
  in responsibility but remain large. Further physical section/formatter
  extraction should continue only with equivalent UI and rendered-DOCX coverage.
- The DPAPI adapter is deliberately not wired to existing repositories until an
  explicit, rollback-safe plaintext-to-encrypted migration is implemented.
- Visual page-by-page comparison of generated DOCX files is still not automated.
- Real camera/image QR-reader fallback chains require hardware/sample-image QA;
  the parser/normalization pipeline is covered.
- Phase 9 packaging verification is recorded after the final build.

### Phase 9 - Portable packaging regression

- PyInstaller one-file build completed successfully with the canonical spec.
- Recursive archive inspection confirmed:
  - the three fixed authorized-person profile asset;
  - before/after-merger administrative data;
  - VSIC business-line data;
  - OpenCV QR detection/super-resolution models;
  - all five business-registration Word templates and their manifest;
  - Min Assistant branding/icon.
- The final executable remained running through a 20-second isolated-AppData
  startup smoke test. The exact test process tree was terminated afterward.
- Artifact: dist/final-refactor/MinAssistant.exe, 244,930,765 bytes.
- SHA-256:
  3302fb6767f521aa4376659394154c43bacd3c3a9cfb75f019a86fe13697f84e.
- PyInstaller emitted the same non-blocking optional-module warnings seen in the
  baseline build; no required runtime asset was reported missing.

## Backup and exact restoration

A source backup alone does not restore the complete app state:

| What must be preserved | Default location |
| --- | --- |
| Source, Git metadata, and uncommitted/untracked work | Entire workspace, including .git and TemplatesBefore/ |
| Current local cases, profiles, and settings | %APPDATA%\Min Assistant |
| Legacy local data that may still be needed for migration | %APPDATA%\Mingo Assistant |
| Exported Word dossiers | %USERPROFILE%\Documents\Min Assistant or the custom export root stored in settings |

If all applicable rows are copied while the app is closed and restored to the
same paths, the source state and local user data can be restored as they were at
backup time. Copying only the Git repository restores code but not AppData or
exported dossiers. A Git checkout/reset also does not preserve uncommitted or
untracked files unless they were copied separately.
