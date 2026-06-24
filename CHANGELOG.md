# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.11.0] - 2026-06-24

Full changelog: https://github.com/crs4/rocrate-validator/compare/0.10.0...0.11.0

### ✨ Added

- feat(profiles): add RO-Crate 1.2 validation profile with comprehensive SHACL shapes and Python checks covering required/recommended/optional properties for Root Data Entity, Data Entities, File Data Entities, Web Data Entities, Contextual Entities, SoftwareApplication, ComputerLanguage, Organization, License, Person, Workflow, Script entities, and detached/referenced RO-Crates ([cb7d3653](https://github.com/crs4/rocrate-validator/commit/cb7d3653))
- feat(profiles/ro-crate-1.2): check recommended entity name and base type for all entities ([41ef61f6](https://github.com/crs4/rocrate-validator/commit/41ef61f6), [c464f526](https://github.com/crs4/rocrate-validator/commit/c464f526))
- feat(profiles/ro-crate-1.2): check recommended reachability of metadata entities ([b4935f81](https://github.com/crs4/rocrate-validator/commit/b4935f81))
- feat(profiles/ro-crate-1.2): check additional license, funder property, and hasPart for Data Entities ([2f673d82](https://github.com/crs4/rocrate-validator/commit/2f673d82), [bbe137e1](https://github.com/crs4/rocrate-validator/commit/bbe137e1), [364cc549](https://github.com/crs4/rocrate-validator/commit/364cc549))
- feat(profiles/ro-crate-1.2): check resolvable identifiers via cite-as property and downloadability via Signposting ([468fe8de](https://github.com/crs4/rocrate-validator/commit/468fe8de), [7b459f34](https://github.com/crs4/rocrate-validator/commit/7b459f34), [bf67d10a](https://github.com/crs4/rocrate-validator/commit/bf67d10a))
- feat(profiles/ro-crate-1.2): check UTF-8 encoding of metadata descriptor and recommended file descriptor naming convention ([00f842b7](https://github.com/crs4/rocrate-validator/commit/00f842b7), [74589852](https://github.com/crs4/rocrate-validator/commit/74589852))
- feat(profiles/ro-crate-1.2): check recommended version property of Software entities and optional alternateName for SoftwareApplication/ComputerLanguage ([2dfd023e](https://github.com/crs4/rocrate-validator/commit/2dfd023e), [364ec58c](https://github.com/crs4/rocrate-validator/commit/364ec58c))
- feat(core): add support for detached metadata files (JSON/JSON-LD as crate source) ([2c7036ac](https://github.com/crs4/rocrate-validator/commit/2c7036ac), [5b6ffea6](https://github.com/crs4/rocrate-validator/commit/5b6ffea6))
- feat(cli): add `--check-availability` / `--no-check-availability` flags for availability control ([5b6ffea6](https://github.com/crs4/rocrate-validator/commit/5b6ffea6))
- feat(shacl): inject default prefixes and improve BNode disambiguation ([2fbfa047](https://github.com/crs4/rocrate-validator/commit/2fbfa047))
- feat(http): reconfigure existing HttpRequester singleton instead of recreating it ([80b15c95](https://github.com/crs4/rocrate-validator/commit/80b15c95))
- ci: add pre-commit configuration with ruff, typos, mypy, and pylint hooks ([e6c3ea46](https://github.com/crs4/rocrate-validator/commit/e6c3ea46), [9fe1a05f](https://github.com/crs4/rocrate-validator/commit/9fe1a05f), [2f498481](https://github.com/crs4/rocrate-validator/commit/2f498481))
- ci: add CSpell dictionary for project-specific terms ([3790e4e9](https://github.com/crs4/rocrate-validator/commit/3790e4e9))

### 🔧 Changed

- refactor(models): split models.py into a package with cohesive submodules ([e662801e](https://github.com/crs4/rocrate-validator/commit/e662801e))
- refactor(rocrate): split rocrate.py into a package with cohesive submodules ([17c6720e](https://github.com/crs4/rocrate-validator/commit/17c6720e))
- refactor(profiles): move RO-Crate 1.1 validation profile to dedicated directory ([71009cc1](https://github.com/crs4/rocrate-validator/commit/71009cc1))
- refactor(shacl): extract node-shape registration helper and helpers to lower complexity ([035494bd](https://github.com/crs4/rocrate-validator/commit/035494bd), [4d0a57b6](https://github.com/crs4/rocrate-validator/commit/4d0a57b6))
- refactor(cli): extract EventDispatcher to route validation events and expose show_overall_result ([a6af0e99](https://github.com/crs4/rocrate-validator/commit/a6af0e99), [f379c448](https://github.com/crs4/rocrate-validator/commit/f379c448))
- refactor: migrate from flake8 to ruff; add ruff.toml configuration with mccabe, eradicate, and pylint-parity rules ([4db08800](https://github.com/crs4/rocrate-validator/commit/4db08800), [cfe6ec4f](https://github.com/crs4/rocrate-validator/commit/cfe6ec4f))
- style: modernize type hints with PEP 604 union syntax (X | Y, X | None) across the codebase ([98426c09](https://github.com/crs4/rocrate-validator/commit/98426c09), [95e05ebb](https://github.com/crs4/rocrate-validator/commit/95e05ebb))
- style: move type-only imports to TYPE_CHECKING blocks and fix import order ([b05efd93](https://github.com/crs4/rocrate-validator/commit/b05efd93), [fb928d07](https://github.com/crs4/rocrate-validator/commit/fb928d07), [d7203517](https://github.com/crs4/rocrate-validator/commit/d7203517), [7871bb18](https://github.com/crs4/rocrate-validator/commit/7871bb18))
- refactor: replace os.path operations with pathlib equivalents across the codebase and tests ([67bb87d5](https://github.com/crs4/rocrate-validator/commit/67bb87d5), [b105c0ed](https://github.com/crs4/rocrate-validator/commit/b105c0ed), [e50fe0dc](https://github.com/crs4/rocrate-validator/commit/e50fe0dc))
- refactor: reduce cyclomatic complexity across validation checks, CLI, and cache modules ([f1c407ee](https://github.com/crs4/rocrate-validator/commit/f1c407ee), [276b9643](https://github.com/crs4/rocrate-validator/commit/276b9643), [e3ed5048](https://github.com/crs4/rocrate-validator/commit/e3ed5048), [d9952040](https://github.com/crs4/rocrate-validator/commit/d9952040), [4614940d](https://github.com/crs4/rocrate-validator/commit/4614940d))
- refactor: replace manual loops with comprehensions and extend(), enumerate, and or-idioms ([1c4bec98](https://github.com/crs4/rocrate-validator/commit/1c4bec98), [4385777c](https://github.com/crs4/rocrate-validator/commit/4385777c), [0c730230](https://github.com/crs4/rocrate-validator/commit/0c730230), [50de8a2e](https://github.com/crs4/rocrate-validator/commit/50de8a2e))
- refactor: replace relative imports with absolute imports ([74b31374](https://github.com/crs4/rocrate-validator/commit/74b31374))
- refactor: use context-managed lock instead of manual acquire/release ([2d7984e8](https://github.com/crs4/rocrate-validator/commit/2d7984e8))
- refactor(console): match rich Console.print signature ([5339b33e](https://github.com/crs4/rocrate-validator/commit/5339b33e))
- build: configure poetry to create in-project virtualenv ([ffcde868](https://github.com/crs4/rocrate-validator/commit/ffcde868))
- build(ruff): set target-version = py310 to align linter with project ([4c3501dd](https://github.com/crs4/rocrate-validator/commit/4c3501dd))
- build(pylint): whitelist SHACL/JSON-LD names and disable R0801 ([5339b33e](https://github.com/crs4/rocrate-validator/commit/5339b33e))

### 🐛 Fixed

- fix(http): resolve session method lazily and reconfigure HttpRequester in place ([9a82482d](https://github.com/crs4/rocrate-validator/commit/9a82482d), [c9b4cc2f](https://github.com/crs4/rocrate-validator/commit/c9b4cc2f), [80b15c95](https://github.com/crs4/rocrate-validator/commit/80b15c95))
- fix(profiles/ro-crate-1.2): correct contentSize check for File DataEntity ([5e7f3120](https://github.com/crs4/rocrate-validator/commit/5e7f3120))
- fix(profiles/ro-crate-1.2): fix conformsTo check for File DataEntity and Root DataEntity identifier ([415bd27d](https://github.com/crs4/rocrate-validator/commit/415bd27d), [919a1421](https://github.com/crs4/rocrate-validator/commit/919a1421))
- fix(profiles/ro-crate-1.2): remove duplicate Web Data Entity checks and fix shape targets ([fbed5c82](https://github.com/crs4/rocrate-validator/commit/fbed5c82), [6877898a](https://github.com/crs4/rocrate-validator/commit/6877898a))
- fix(profiles): raise ProfileNotFound when profile is not found in get_profile ([fdbbc1e2](https://github.com/crs4/rocrate-validator/commit/fdbbc1e2))
- fix(profiles): show actual size in Web Data Entity contentSize mismatch message ([51e7a767](https://github.com/crs4/rocrate-validator/commit/51e7a767))
- fix(models): add missing return statement and call as_json() before as_graph() ([ff196b4a](https://github.com/crs4/rocrate-validator/commit/ff196b4a), [667d8b93](https://github.com/crs4/rocrate-validator/commit/667d8b93))
- fix(typing): add None guards, implicit Optional annotations, and missing type annotations across the codebase ([4156d7d8](https://github.com/crs4/rocrate-validator/commit/4156d7d8), [dda588ae](https://github.com/crs4/rocrate-validator/commit/dda588ae), [e39e28b1](https://github.com/crs4/rocrate-validator/commit/e39e28b1))
- fix(shacl): return real bool from SHACLCheck.check and is_external_reference ([982e3257](https://github.com/crs4/rocrate-validator/commit/982e3257), [896b419d](https://github.com/crs4/rocrate-validator/commit/896b419d))
- fix(logging): fall back to WARNING for unknown log level names ([b586b973](https://github.com/crs4/rocrate-validator/commit/b586b973))
- fix(progress): respect severity threshold in progress tracking ([43ce7a15](https://github.com/crs4/rocrate-validator/commit/43ce7a15))
- fix(utils): fix logger factory and add exception chaining ([5afa76a3](https://github.com/crs4/rocrate-validator/commit/5afa76a3), [f672de2b](https://github.com/crs4/rocrate-validator/commit/f672de2b))
- fix(utils): improve dynamic module loading to avoid collisions ([997a3c5d](https://github.com/crs4/rocrate-validator/commit/997a3c5d))
- fix(services): guard original_data_path against None on restore ([bcbbdc34](https://github.com/crs4/rocrate-validator/commit/bcbbdc34))
- fix(isa-ro-crate): terminate isa-ro-crate:Data triple in ontology.ttl ([f4fd0446](https://github.com/crs4/rocrate-validator/commit/f4fd0446))
- fix(test): use str() instead of as_uri() for local crate paths and fix context manager on Path ([4b3d5847](https://github.com/crs4/rocrate-validator/commit/4b3d5847), [b15e301b](https://github.com/crs4/rocrate-validator/commit/b15e301b))
- fix: add explicit encoding="utf-8" to open() calls and read_text ([c73e6b2e](https://github.com/crs4/rocrate-validator/commit/c73e6b2e), [8de1aa68](https://github.com/crs4/rocrate-validator/commit/8de1aa68))
- fix: add proper exception chaining in except blocks ([b18d02ac](https://github.com/crs4/rocrate-validator/commit/b18d02ac))
- fix: use bare raise instead of raise e and ValueError instead of generic Exception ([ba2ef280](https://github.com/crs4/rocrate-validator/commit/ba2ef280), [5d00a4fc](https://github.com/crs4/rocrate-validator/commit/5d00a4fc))

### 🗑️ Removed

- chore: remove flake8 config and dependency ([c7286047](https://github.com/crs4/rocrate-validator/commit/c7286047), [35095f82](https://github.com/crs4/rocrate-validator/commit/35095f82))
- chore(cspell): remove stale ignore entries ([85d3e9b8](https://github.com/crs4/rocrate-validator/commit/85d3e9b8))

### 📚 Documentation

- docs(readme): add Development section with pre-commit usage ([686db620](https://github.com/crs4/rocrate-validator/commit/686db620))
- docs(log): convert usage example from commented code to docstring ([d21aa857](https://github.com/crs4/rocrate-validator/commit/d21aa857))

## [0.10.0] - 2026-06-01

Full changelog: https://github.com/crs4/rocrate-validator/compare/0.9.0...0.10.0

### ✨ Added

- feat(cli): add offline mode with an `--offline` flag and an HTTP `cache` subcommand to validate RO-Crates without network access ([e296f10](https://github.com/crs4/rocrate-validator/commit/e296f10), [f8b99bc](https://github.com/crs4/rocrate-validator/commit/f8b99bc))
- feat(utils): add a cache-aware JSON-LD document loader and HTTP cache warm-up from profile artifacts ([eedabf1](https://github.com/crs4/rocrate-validator/commit/eedabf1), [949ec6f](https://github.com/crs4/rocrate-validator/commit/949ec6f))
- feat(utils): add offline mode and cache management to `HttpRequester`, with configurable cache path ([c92d88c](https://github.com/crs4/rocrate-validator/commit/c92d88c), [7c9e825](https://github.com/crs4/rocrate-validator/commit/7c9e825))
- feat(core): support offline mode when downloading remote RO-Crates ([57eceb5](https://github.com/crs4/rocrate-validator/commit/57eceb5))
- feat(cli/cache): add `cache list` (alias `ls`) and allow caching of explicit URLs via `cache warm` ([f9b43ae](https://github.com/crs4/rocrate-validator/commit/f9b43ae), [6925d55](https://github.com/crs4/rocrate-validator/commit/6925d55))
- feat(cli): extend the `describe` command to describe individual requirement checks ([f3fb7f3](https://github.com/crs4/rocrate-validator/commit/f3fb7f3))
- feat(model): add a `SourceSnippet` class and `RequirementCheck.get_source_snippet`, implemented for both SHACL and Python checks ([9f48674](https://github.com/crs4/rocrate-validator/commit/9f48674), [25bc7b4](https://github.com/crs4/rocrate-validator/commit/25bc7b4), [fe740e4](https://github.com/crs4/rocrate-validator/commit/fe740e4))
- feat(checks): support a `deactivated` flag on `RequirementCheck` to override/deactivate checks by name for Python and SHACL ([dd84c32](https://github.com/crs4/rocrate-validator/commit/dd84c32), [4196f0e](https://github.com/crs4/rocrate-validator/commit/4196f0e))
- feat(rocrate): add `check_availability()` with `AvailabilityStatus` on entities and granular remote-scheme classification ([76e92a4](https://github.com/crs4/rocrate-validator/commit/76e92a4), [469bbe5](https://github.com/crs4/rocrate-validator/commit/469bbe5))
- feat(checks): handle `UNAUTHORIZED`/`UNCHECKABLE` web data entities as warnings ([0196dc9](https://github.com/crs4/rocrate-validator/commit/0196dc9))
- feat(uri): add an `is_external_reference()` scheme detector ([62f89c0](https://github.com/crs4/rocrate-validator/commit/62f89c0))
- feat(model): extend the `Profile` model to compute descendants ([a9783ce](https://github.com/crs4/rocrate-validator/commit/a9783ce))
- ISA profile: add RDF classes for ISA types and a dedicated `Process` class for process checks ([3ff4245](https://github.com/crs4/rocrate-validator/commit/3ff4245), [e3fda59](https://github.com/crs4/rocrate-validator/commit/e3fda59), [c3e2d5f](https://github.com/crs4/rocrate-validator/commit/c3e2d5f))

### 🔧 Changed

- refactor(models): introduce pre/post internal validation hooks on `Validator` ([e43364b](https://github.com/crs4/rocrate-validator/commit/e43364b))
- refactor(SHACL): rewrite `build_node_subgraph` as an iterative BNode traversal ([23164b7](https://github.com/crs4/rocrate-validator/commit/23164b7))
- refactor(errors): accept `str`, `Path` or `URI` in `ROCrateInvalidURIError` ([0b8289b](https://github.com/crs4/rocrate-validator/commit/0b8289b))
- refactor(cli/cache): drop the `Status` column from the `cache list` table ([392df1a](https://github.com/crs4/rocrate-validator/commit/392df1a))
- feat(constants): default the HTTP cache to never expire ([419fece](https://github.com/crs4/rocrate-validator/commit/419fece))

### 🐛 Fixed

- fix(shacl): build property shape subgraphs by reachability and derive `NodeShape` level from nested `PropertyShape`s ([f1c0cfd](https://github.com/crs4/rocrate-validator/commit/f1c0cfd), [50448145](https://github.com/crs4/rocrate-validator/commit/5044814))
- fix(shacl): evaluate inherited shapes for zero-shape target profiles ([bcb5cac](https://github.com/crs4/rocrate-validator/commit/bcb5cac))
- fix(shacl): drop sub-threshold PySHACL violations at the source ([254fb88](https://github.com/crs4/rocrate-validator/commit/254fb88))
- fix(core): filter failed requirements/checks by the configured severity ([a306f7f](https://github.com/crs4/rocrate-validator/commit/a306f7f))
- fix(models): forward `extra_profiles_path` when computing validation statistics ([7b3e8bc](https://github.com/crs4/rocrate-validator/commit/7b3e8bc))
- fix(uri): treat `file://` URIs with a non-local authority as remote ([63acb6a](https://github.com/crs4/rocrate-validator/commit/63acb6a))
- fix(cli/cache): resolve profile tokens in `cache warm` and avoid `stream=True` when fetching remote crates ([7926832](https://github.com/crs4/rocrate-validator/commit/7926832), [33012b6](https://github.com/crs4/rocrate-validator/commit/33012b6))
- fix(validation): report offline cache misses once per URL ([757b86a](https://github.com/crs4/rocrate-validator/commit/757b86a))
- fix(ISA): correct the error message for a bad position in `HowToStep` ([03a32fc](https://github.com/crs4/rocrate-validator/commit/03a32fc))

### 📚 Documentation

- docs: add a dedicated documentation page for the cache and offline mode features ([e10c3b5](https://github.com/crs4/rocrate-validator/commit/e10c3b5))
- docs(profiles): document check override-by-name and deactivation ([0b6bff7](https://github.com/crs4/rocrate-validator/commit/0b6bff7))

## [0.9.0] - 2026-04-20

Full changelog: https://github.com/crs4/rocrate-validator/compare/0.8.1...0.9.0

### ✨ Added

- feat(profiles/isa): add the ISA RO-Crate profile, with checks and tests for Investigation, Study, Assay, Process, Protocol, Sample, Data, Person and PropertyValue entities ([852fb23](https://github.com/crs4/rocrate-validator/commit/852fb23), [d62e214](https://github.com/crs4/rocrate-validator/commit/d62e214), [727b6f0](https://github.com/crs4/rocrate-validator/commit/727b6f0))
- feat(cli): add CLI options to configure the HTTP cache (`--cache-path`, `--cache-max-age`) ([564230f](https://github.com/crs4/rocrate-validator/commit/564230f))
- feat(model): enable cache configuration in `ValidationSettings` ([b2b47ba](https://github.com/crs4/rocrate-validator/commit/b2b47ba))
- feat(utils): extend the `HttpRequester` constructor to support cache configuration parameters ([2f2a873](https://github.com/crs4/rocrate-validator/commit/2f2a873))
- feat(ro-crate): refine the constraint enforcing metadata descriptor existence ([2c6ea76](https://github.com/crs4/rocrate-validator/commit/2c6ea76))
- feat(file-descriptor): add an internal remote-context retrieval method supporting the alternate `Link` header ([f8b0e55](https://github.com/crs4/rocrate-validator/commit/f8b0e55))

### 🔧 Changed

- refactor(ro-crate): relax the `ROCrateMetadataFileDescriptor` class definition ([61ddbb5](https://github.com/crs4/rocrate-validator/commit/61ddbb5))
- refactor(file-descriptor): route checks through the new remote-context retrieval method ([0ce2619](https://github.com/crs4/rocrate-validator/commit/0ce2619))
- chore(utils): increase the session cache max age to 300 seconds ([36ca0ac](https://github.com/crs4/rocrate-validator/commit/36ca0ac))
- ci(gh-actions): update outdated GitHub Actions ([d565c5d](https://github.com/crs4/rocrate-validator/commit/d565c5d))

### 🐛 Fixed

- fix(ro-crate): target metadata descriptor shapes by class and select the candidate descriptor via SPARQL ([8219f27](https://github.com/crs4/rocrate-validator/commit/8219f27), [39bd761](https://github.com/crs4/rocrate-validator/commit/39bd761), [1a91aa4](https://github.com/crs4/rocrate-validator/commit/1a91aa4))
- fix(shacl): extract `@base` from the JSON-LD document for ontology parsing ([57f5c54](https://github.com/crs4/rocrate-validator/commit/57f5c54))
- fix(SHACL-core): improve SHACL violation parsing with better error handling ([90a9f06](https://github.com/crs4/rocrate-validator/commit/90a9f06))
- fix(file-descriptor): accept `application/json` and treat the `Link` header case-insensitively for remote context retrieval ([fe5ba1c](https://github.com/crs4/rocrate-validator/commit/fe5ba1c))
- fix(file-descriptor): refine the compacted JSON-LD key validation logic ([45a7017](https://github.com/crs4/rocrate-validator/commit/45a7017))
- fix(core): allow terms defined by context prefixes ([5fe8171](https://github.com/crs4/rocrate-validator/commit/5fe8171))
- fix(core): fix output formatting ([523fbf4](https://github.com/crs4/rocrate-validator/commit/523fbf4))

### 📚 Documentation

- docs(cli): document the `-1` value for no cache expiration in the `--cache-max-age` help ([c5848bc](https://github.com/crs4/rocrate-validator/commit/c5848bc))

## [0.8.1] - 2026-02-18

Full changelog: https://github.com/crs4/rocrate-validator/compare/0.8.0...0.8.1

### 🔧 Changed

- refactor(core): rename flag `disable_inherited_profiles_reporting` to `disable_inherited_profiles_issue_reporting` ([daebea1](https://github.com/crs4/rocrate-validator/commit/daebea1))
- refactor(core): set `disable_inherited_profiles_issue_reporting` to disabled by default ([c8e7de7](https://github.com/crs4/rocrate-validator/commit/c8e7de7))
- refactor(core): skip inherited profile event notifications when issue reporting is disabled ([c8ad7b9](https://github.com/crs4/rocrate-validator/commit/c8ad7b9))
- build(poetry): allow using the latest PySHACL version ([fde97be](https://github.com/crs4/rocrate-validator/commit/fde97be))

### 🐛 Fixed

- fix(cli): fix `rich` deprecation warning ([dbdfae5](https://github.com/crs4/rocrate-validator/commit/dbdfae5))
- fix(core): ensure skipped checks are reported properly ([471745b](https://github.com/crs4/rocrate-validator/commit/471745b))
- fix(cli): wrong param name ([38f22ff](https://github.com/crs4/rocrate-validator/commit/38f22ff))
- fix(core): ensure skip_checks is defined before use ([04988b1](https://github.com/crs4/rocrate-validator/commit/04988b1))
- fix(core): enable skipping of Python checks ([efcad8b](https://github.com/crs4/rocrate-validator/commit/efcad8b))
- fix(core): enable skipping of SHACL checks ([9141a72](https://github.com/crs4/rocrate-validator/commit/9141a72))
- fix(core): exclude skipped checks from stats ([4a27eb9](https://github.com/crs4/rocrate-validator/commit/4a27eb9))
- fix(core): remove inherited checks from stats when `disable_inherited_profiles_issue_reporting` is set ([f6e15b7](https://github.com/crs4/rocrate-validator/commit/f6e15b7))
- fix(cli): make the `disable_profile_inheritance` CLI flag affect only reporting (not loading) of inherited profiles ([d6f9192](https://github.com/crs4/rocrate-validator/commit/d6f9192))

### 🗑️ Removed

- chore: filter `rdflib` JSON-LD deprecation warnings ([c6da40a](https://github.com/crs4/rocrate-validator/commit/c6da40a))

### 📚 Documentation

- docs(core): clarify the proper usage of the `enable_profile_inheritance` flag ([cd3af57](https://github.com/crs4/rocrate-validator/commit/cd3af57))
- docs(core): improve code documentation with additional comments ([cd03486](https://github.com/crs4/rocrate-validator/commit/cd03486))

## [0.8.0] - 2026-01-07

### ✨ Added

- feat(cli): detect environment and properly handle Console initialization
- feat(profiles/ro-crate): check if the JSON-LD context can be loaded
- feat(profiles/ro-crate): check for the compacted JSON-LD format of the file descriptor
- feat(profiles/ro-crate): check recommended existence of absolute local data entities
- feat(profiles/ro-crate): update check to skip absolute paths
- feat(core): extend entity model to detect local and relative paths
- feat(profiles/ro-crate): check for the existence of data entities
- feat(cli): allow configuring the list of checks to skip via CLI
- feat(core): allow skipping a configurable list of checks
- feat(cli): display the full check identifier when verbose mode is enabled
- feat(core): fix and extend method to fetch entities by type
- feat(core): add utility method to retrieve all data entities
- feat(core): expose path/uri of rocrate entities
- feat(core): add class method to derive data entity path from identifier
- feat(cli): add support for relative root path option
- feat(model): allow instantiating metadata-only RO-Crates
- feat(services): add a service method to validate RO-Crate metadata from a dict
- feat(profiles/ro-crate): extend flat JSON-LD check to support value objects
- feat(core): add factory method to automatically instantiate RO-Crate with the correct subtype
- feat(model): add classes for handling BagIt-wrapped RO-Crates

### 🔧 Changed

- refactor(utils): reorganize the `utils` package structure
- refactor(utils): rename `rocv_io` to `io_helpers`
- refactor(utils): move rocv_io into the utils package
- refactor(core): convert utils module into a package
- refactor(io.output): restructure and simplify the formatter classes
- refactor(io.output): simplify Console class
- refactor(cli): restructure CLI output handling logic
- refactor(cli): move and extend the base class to handle console output
- refactor(io.output): move the Pager class to a dedicated module
- refactor(cli): move input methods to the `io.input` module
- refactor(model): move profile finder to the Profile class
- refactor(core): improve file and directory availability checks
- refactor(core): refactor entity availability check with generic ZIP support and path unquoting
- refactor(cli): remove CLI parameters from the global validation settings
- refactor(core): move the init logic to the `__post__init__` method
- refactor(profiles/ro-crate): move required properties to a dedicated shape
- refactor(core): declare the function as class level method
- refactor(core): simplify profiles parsing
- refactor(core): rewrite magic method to sort profiles
- refactor(cli): update the short option to skip checks
- refactor(core): use method to identify remote entities
- refactor(core): remove redundant code
- refactor(utils): refactor multiple delegator methods into one
- refactor(core): remove relative imports
- refactor(core): adopt the `HttpRequester` class
- refactor(shacl): only exclude fragment identifiers that refer to the root data entity
- refactor(core): refactor Python detection of local identifiers

### 🐛 Fixed

- fix(profiles/ro-crate): fix SHACL nodeKind constraint being too strict
- fix(cli): wrong param name
- fix(core): ensure skip_checks is defined before use
- fix(core): enable skipping of Python checks
- fix(core): enable skipping of SHACL checks
- fix(core): exclude skipped checks from stats
- fix(core): remove inherited checks from stats when `disable_inherited_profiles_issue_reporting` is set
- fix(cli): make the `disable_profile_inheritance` CLI flag affect only reporting
- fix(tests): fix unit test assertion
- fix(logging): fix typo
- fix(cli): missing object dump
- fix(core): fix the candidate profiles collection
- fix(io.output): fix import
- fix(io.output): allow initialization of the report layout without an initial state
- fix(cli): fix formatter parameter
- fix(cli): restructure logic to process CLI text output of validation result
- fix(io.output): fix missing padding
- fix(model): fix availability check of external resources
- fix(model): use the custom class for remote Bagit RO-Crate objects
- fix(model): fix initialisation of BagitROCrate objects
- fix(model): fix fallback value for root path
- fix(model): fix initialisation of Bagit objects
- fix(model): fix linter warnings
- fix(model): fix linter warning E999
- fix(profiles/ro-crate): trailing slash for Data Entities is recommended not mandatory
- fix(profiles/ro-crate): fix `sh:message` for the required `datePublished`

### 🗑️ Removed

- chore: filter `rdflib` JSON-LD deprecation warnings
- chore(poetry): fix missing whitespaces
- chore: update copyright notice to 2026
- chore(git): ignore IDE project files

### 📚 Documentation

- docs(api): update docs
- docs(profiles): add note about ontology graph support and formal definitions
- docs(io.output): add some note about output formatters
- docs(readme): specify python 3.9 or later
- docs(profiles/ro-crate): add notes on custom validation profiles
- docs(cli): rephrase `--skip-checks` option description
- docs(cli): improve description of the `skip-checks` option
- docs(cli): add notes about programmatic metadata-only validation
- docs(core): clarify the proper usage of the `enable_profile_inheritance` flag
- docs(core): improve code documentation with additional comments

### ⚡ Performance

- perf(io.output): remove padding when using using no color console
- perf(cache): optimize Redis connection pooling
- perf(shacl): skip redundant violation messages
- perf(core): compute overrides on the fly
- perf(core): add a method to find a profile by checking its name
- perf(core): add properties to get parents and siblings of a given profile
- perf(core): add getter for sibling profiles
- perf(core): automatically detect overrides during Profile initialization
- perf(core): add support for overrides to the `Profile` model

## [0.7.3] - 2025-06-23

### 🐛 Fixed

- Restore Python 3.13 compatibility

## [0.7.2] - 2025-06-19

### 🔧 Changed

- Allow pyshacl 0.30
- Adjust dependency version ranges for better flexibility

## [0.7.1] - 2025-05-20

### 🔧 Changed

- Upgrade dependencies

## [0.7.0] - 2025-05-16

### ✨ Added

- feat(profiles/ro-crate): exclude from the definition of Dataset Data Entities any dataset with a local identifier
- feat(profiles/ro-crate): exclude from the definition of File Data Entities any file with a local identifier
- feat(profiles/ro-crate): including files with local identifiers in the crate is not mandatory

### 🔧 Changed

- refactor(shacl): only exclude fragment identifiers that refer to the root data entity
- refactor(core): refactor Python detection of local identifiers

## [0.6.5] - 2025-04-30

### ✨ Added

- feat(core): allow avoiding duplicated events

### 🔧 Changed

- refactor(shacl): fix issue notifications
- chore(core): update log and comment messages

### 🐛 Fixed

- fix(shacl): fix return value of SHACL requirement check
- fix(core): do not skip overridden checks of the target profile
- fix(shacl): keep track of the checks that have been notified

## [0.6.4] - 2025-04-24

### ✨ Added

- feat(utils): add multithreading support
- feat(utils): add a singleton class to handle HTTP requests

### 🔧 Changed

- refactor(utils): refactor multiple delegator methods into one
- refactor(core): remove relative imports
- refactor(core): adopt the `HttpRequester` class

## [0.6.3] - 2025-03-25

### 🐛 Fixed

- fix(cli): don't skip overridden checks of the target profile

### 🔧 Changed

- chore: update copyright notice

## [0.6.2] - 2025-03-12

### ✨ Added

- feat(core): add method to list the entries of a ZIP archive
- feat(core): add getter for archive entry info

### 🔧 Changed

- refactor(core): allow empty files and directories within a ZIP file
- Acknowledge CN HPC

### 🐛 Fixed

- fix(core): update logic to check the availability of archive folders
- fix(cli): fix typo

## [0.6.1] - 2025-02-20

### 🐛 Fixed

- fix(core): fix the candidate profiles collection

### 🔧 Changed

- chore: update github action version

## [0.6.0] - 2025-02-06

### ✨ Added

- feat(profiles/ro-crate): check if the JSON-LD context can be loaded
- feat(profiles/ro-crate): check for the compacted JSON-LD format of the file descriptor
- feat(profiles/ro-crate): check recommended existence of absolute local data entities
- feat(profiles/ro-crate): update check to skip absolute paths
- feat(core): extend entity model to detect local and relative paths
- feat(profiles/ro-crate): check for the existence of data entities
- feat(cli): allow configuring the list of checks to skip via CLI
- feat(core): allow skipping a configurable list of checks
- feat(cli): display the full check identifier when verbose mode is enabled
- feat(core): fix and extend method to fetch entities by type
- feat(core): add utility method to retrieve all data entities
- feat(core): expose path/uri of rocrate entities
- feat(core): add class method to derive data entity path from identifier
- feat(cli): check the minimum required Python version
- feat(utils): add utility functions to read and check the minimum required Python version

### 🔧 Changed

- refactor(cli): remove CLI parameters from the global validation settings
- refactor(core): move the init logic to the `__post__init__` method
- refactor(profiles/ro-crate): move required properties to a dedicated shape
- refactor(core): declare the function as class level method
- refactor(core): simplify profiles parsing
- refactor(core): rewrite magic method to sort profiles
- refactor(cli): update the short option to skip checks
- refactor(core): use method to identify remote entities
- refactor(core): remove redundant code
- refactor(core): rename method arguments
- refactor(core): rename method
- refactor(core): remove redundant method
- refactor(core): remove cache timeout from validation settings
- refactor(core): remove unused `ontology_path` setting
- refactor(core): rename the flag to disable downloading a remote crate
- refactor(core): rename flag to disable reporting of inherited checks
- refactor(core): rename property to enable profile inheritance
- refactor(core): link the context with the settings as an object
- refactor(core): init and validate URI on settings object
- refactor(core): remove unused imports
- refactor(core): rename input parameter for the ro-crate uri
- refactor(core): remove internal settings from the `ValidationSettings` interface

### 🐛 Fixed

- fix(profiles/ro-crate): fix SHACL nodeKind constraint being too strict
- fix(cli): wrong param name
- fix(core): ensure skip_checks is defined before use
- fix(core): enable skipping of Python checks
- fix(core): enable skipping of SHACL checks
- fix(core): exclude skipped checks from stats
- fix(core): remove inherited checks from stats when `disable_inherited_profiles_issue_reporting` is set
- fix(cli): make the `disable_profile_inheritance` CLI flag affect only reporting
- fix(profiles/ro-crate): trailing slash for Data Entities is recommended not mandatory

### 📚 Documentation

- docs(readthedocs): add copyright
- docs(readthedocs): mention the fallback profile
- docs(readthedocs): restructure toc
- docs(readthedocs): fix typos
- docs(readthedocs): rewrite note
- docs(readthedocs): reformat
- docs(readthedocs): update toc
- docs(readthedocs): rename api docs file
- docs(readthedocs): more details on profile detection and versioning
- docs(readthedocs): add an initial "How it works" section
- docs(readthedocs): add link to Github repository
- docs(readthedocs): dynamically set the version
- docs(readthedocs): fix copyright
- docs(diagrams): extend diagrams by adding captions
- docs(diagrams): fix svg width
- docs(diagrams): fix missing `by`
- docs(readthedocs): update flag description
- docs(core): don't expose an internal validate method
- docs(core): extend param description
- docs(diagrams): update diagrams
- docs(diagrams): fix missing link
- docs(diagrams): fix blanks
- docs(diagrams): add missing params
- docs: add diagram for the `profiles` service
- docs: add diagram for the `validate` service
- docs: fix link
- docs: move the diagram files
- docs: refine "Core Model" diagram
- docs(core): update docstring
- docs(core): add docstring of `ValidationSettings` class
- docs(readme): reformat note
- docs(readme): extend the list of features
- docs(core): improve code documentation
- docs(core): add docstrings to the `ValidationResult` class
- docs(readme): add a comment on `profile_identifier`
- docs(readme): simplify path to crate in the programmatic validation example
- docs(readme): update list of supported profiles
- docs: add minimal example of programmatic usage
- docs: reformat
- docs(readme): extend example
- docs(core): add a docstring for the `violatingPropertyValue`
- docs(readme): add badge to the readthedocs documentation
- docs(core): bootstrap sphinx documentation

### ⚡ Performance

- perf(shacl): skip redundant violation messages
- perf(core): compute overrides on the fly
- perf(core): add a method to find a profile by checking its name
- perf(core): add properties to get parents and siblings of a given profile
- perf(core): add getter for sibling profiles
- perf(core): automatically detect overrides during Profile initialization
- perf(core): add support for overrides to the `Profile` model

## [0.5.0] - 2024-12-17

### ✨ Added

- feat(cli): swap default behaviour for fail fast
- feat(core): swap default behaviour `fail fast` option in API settings
- feat: add provenance run crate profile
- feat(profiles/provenance-run-crate): check `connection` property on `HowToStep` instances
- feat(profiles/provenance-run-crate): check `connection` property on computational workflow instances
- feat(profiles/provenance-run-crate): check if ParameterConnection instances are referenced through connections
- feat(core): add property to denote the format of the JSON output

### 🔧 Changed

- refactor(core): rename the property to indicate the validator version in the JSON output
- refactor(shacl): avoid code repetition
- refactor(core): reorder method args
- refactor(core): rename method arguments
- refactor(core): rename method
- refactor(core): remove redundant method
- refactor(core): remove cache timeout from validation settings
- refactor(core): remove unused `ontology_path` setting
- refactor(core): rename the flag to disable downloading a remote crate
- refactor(core): rename flag to disable reporting of inherited checks
- refactor(core): rename property to enable profile inheritance
- refactor(core): link the context with the settings as an object
- refactor(core): init and validate URI on settings object
- refactor(core): remove unused imports
- refactor(core): rename input parameter for the ro-crate uri
- refactor(core): remove internal settings from the `ValidationSettings` interface
- refactor(core): rename some properties of the `ValidationResult` class
- refactor(services): the `profile_identifier` should be a positional argument
- refactor(core): update the representation of the `ValidationResult` object
- refactor(shacl): mark internal methods
- refactor(core): rename link property between result and RO-Crate URI
- refactor(core): rename some CheckIssue properties
- refactor(services): remove unused function argument
- refactor(core): rename the parameter for ROCrate instantiation
- refactor(core): use more descriptive names for `resultPath` and `focusNode`
- refactor(core): update `CheckIssue` representation
- refactor(core): improve the readability of the identifier
- refactor(core): add a docstring to the main validation classes
- refactor(cli): always include the `profile_identifiers` property in the json output format
- refactor(cli): move test data to the appropriate path
- refactor(profiles): move test data to the appropriate path
- refactor(profiles/provenance-run-crate): use validator prefixes to denote shapes

### 🐛 Fixed

- fix(shacl): preserve issues with identical messages for different entities
- fix(profiles/provenance-run-crate): allow the position property of steps to accept integer values
- fix(readthedocs): minor changes
- fix(docs): raw html object to include the diagram
- fix(readthedocs): fix missing dependency
- fix(shacl): typo
- fix(core): typo
- fix(shacl): avoid repeating errors
- fix(core): fix severity detection of Python checks
- fix(core): determine the issue level and severity based on the check
- fix(profiles/workflow-run-crate): fix missing f-string formatting

### 📚 Documentation

- docs(profiles/provenance-run-crate): add copyright notice

### ⚡ Performance

- perf(core): compute overrides on the fly
- perf(core): add a method to find a profile by checking its name
- perf(core): add properties to get parents and siblings of a given profile
- perf(core): add getter for sibling profiles
- perf(core): automatically detect overrides during Profile initialization
- perf(core): add support for overrides to the `Profile` model

## [0.4.6] - 2024-11-13

### 🐛 Fixed

- fix: RO-Crate validation should work for nested properties without id

## [0.4.5] - 2024-11-08

### ✨ Added

- feat: allow to exit cli from pager on unix
- feat: allow to exit cli during interactive input on unix

## [0.4.4] - 2024-11-07

### ✨ Added

- feat(core): add the ability to hide Python requirements
- feat(profile/ro-crate): validate ro-crate metadata is flattened
- feat(core): always validate the ROCrate URI before instantiating the corresponding object
- feat(utils): add function to validate a RO-Crate URI parameter

### 🔧 Changed

- refactor(utils): update the error message for resource unavailability
- refactor(cli): delegate URI validation from the CLI to the utility function
- refactor(utils): use the updated `ROCrateInvalidURIError` class
- refactor(utils): set a default error message in the `ROCrateInvalidURIError` class

### 🐛 Fixed

- fix(utils): fix string format of error message
- fix(core): allow to exit cli from pager on unix
- fix(core): allow to exit cli during interactive input on unix

## [0.4.3] - 2024-11-06

### ✨ Added

- feat(cli): check the minimum required Python version
- feat(utils): add utility functions to read and check the minimum required Python version
- feat(profile/ro-crate): more comprehensive pattern to detect valid ISO 8601 dates
- feat(profile/ro-crate): add check for recommended values of the `RootDataEntity` `datePublished` property
- feat(shacl): add root requirement check
- feat(shacl): extend SHACL check initialisation
- feat(shacl): extend model to mark root requirement checks
- feat(core): extend model to include hidden requirement checks

### 🔧 Changed

- build(python): update the minimum python version to 3.9.20
- refactor(shacl): restructure the initialisation of shack checks
- refactor(shacl): restructure the logic to set and retrieve the requirement level in SHACL checks
- refactor(cli): update `profiles list` to show the number of checks by severity
- refactor(cli): restructure fn to generate checks stats
- refactor(core): update `get_requirements` method
- refactor(core): remove `level` property from the `Requirement` model
- refactor(core): update `Requirement` identifier
- refactor(core): update the requirements loading process
- refactor(shacl): clean up

### 🐛 Fixed

- fix(cli): skip counting overridden checks
- fix(cli): do not skip overridden checks when they belong to the target profile
- fix(shacl): fix property getter
- fix(profiles/ro-crate): fix severity of WebDataEntity shapes
- fix(shacl): fix the override of the base method
- fix(shacl): always parse the result graph
- fix(profiles/ro-crate): fix mismatch in the requirement level
- fix(core): fix LevelCollection getter
- fix(core): wrong property name
- fix(core): properly initialize `PyRequirement` instances
- fix(shacl): use the shape description
- fix(shacl): fix condition to print the mismatch warning
- fix(core): fix in progress for detecting overrides
- fix(profiles/ro-crate): fix inconsistent severity level

## [0.4.2] - 2024-10-30

### ✨ Added

- feat(core): add property to denote the format of the JSON output

### 🔧 Changed

- refactor(core): rename the property to indicate the validator version in the JSON output

## [0.4.1] - 2024-10-30

### ✨ Added

- feat(core): add `to_dict` serializer methods
- feat(core): extend check info on JSON output
- feat(core): add minimal dict serializers for the Profile and RequirementCheck models

### 🔧 Changed

- refactor(core): add rocrate-validator version to the JSON output
- refactor(core): remove `rocrate` path property from JSON output
- refactor(core): remove `data_path` and `profiles_path` from JSON output
- refactor(core): remove `resultPath` from issue serialisation
- refactor(shacl): expose `node_name` getter

### 🐛 Fixed

- fix(core): fix severity detection of Python checks
- fix(core): determine the issue level and severity based on the check associated with the issue
- fix(profiles/workflow-run-crate): fix missing f-string formatting

### 📚 Documentation

- docs(profiles/workflow-run-crate): add copyright notice

## [0.4.0] - 2024-10-24

### ✨ Added

- feat(profiles/provenance-run-crate): check `connection` property on `HowToStep` instances
- feat(profiles/provenance-run-crate): check `connection` property on computational workflow instances
- feat(profiles/provenance-run-crate): check if ParameterConnection instances are referenced through connections
- feat(profiles/provenance-run-crate): add provenance run crate profile

### 🔧 Changed

- refactor(profiles/provenance-run-crate): use validator prefixes to denote shapes

## [0.3.0] - 2024-10-11

### ✨ Added

- feat(core): declare package version
- feat(utils): enhance version detection: take Git repository state into account
- feat(profiles/workflow-run-crate): add workflow run crate profile

### 🔧 Changed

- build: rename package to `roc-validator`
- build: update package version number
- refactor(ci): restructure testing pipeline
- refactor(ci): restructure release pipeline
- refactor(core): use the `severity` property to denote the severity level of a Python requirement
- refactor(cli): remove short option for `profiles_path`
- refactor(profiles/ro-crate): move WebDataEntity shapes
- refactor(shacl): restructure the logic to set/get requirement level on SHACL checks
- refactor(core): update `Requirement.level` definition
- refactor(core): update the requirements loading process
- refactor(shacl): set the conforms property to be computed based on the presence of issues
- refactor(core): fix the sorting criteria of the requirements
- refactor(core): safer way to add candidate profiles
- refactor(cli): fix output of `profiles describe` command
- refactor(cli): disable ontologies parameter
- refactor(utils): generic function to load graphs from paths
- refactor: move code to the rocrate-validator folder
- refactor: move ttl file
- refactor: move code to the src folder

### 🐛 Fixed

- fix(profiles/ro-crate): change severity of the `RootDataEntity` properties
- fix(profiles/ro-crate): fix `sh:message` for the required `datePublished`
- fix(cli): disable pagination on Windows systems
- fix(logging): update logging configuration
- fix(shacl): report a generic error when the metadata is invalid
- fix(core): fix the sorting criteria of the requirements
- fix(profiles/ro-crate): fix inconsistent severity level
- fix(ci): update error message
- fix(ci): fix the command to check the tool version
- fix(ci): add missing steps

### 📚 Documentation

- docs(readme): add `pip` as installation method
- docs(readme): reorder status badges
- docs(readme): add PyPI version badge
- docs(readme): add build status badge
- docs(readme): update testing status and license badges
- docs: enrich the package metadata
- docs(readme): add installation instructions
- docs(readme): add usage instructions
- docs(readme): add supported profiles section
- docs(readme): add features section
- docs(readme): add badges

### ⚡ Performance

- perf(shacl): filter shapes based on the requirement level
- perf(shacl): set the check severity based on the declared value, or infer it from the path
- perf(shacl): allow to get declared `severity` of a Shape Node

## [0.2.1] - 2024-09-25

### 🐛 Fixed

- fix: fix version parser

## [0.2.0] - 2024-09-25

### ✨ Added

- feat(ci): restructure testing pipeline
- feat(ci): restructure release pipeline
- feat(core): allow to specify the `level` of a Python requirement
- feat(shacl): filter shapes based on the requirement level
- feat(shacl): set the check severity based on the declared value, or infer it from the path
- feat(shacl): allow to get declared `severity` of a Shape Node
- feat(services): expose the severity property in the `get_profile` service
- feat(shacl): enable info and warning severity levels in PySHACL
- feat(core): add `{severity,requirement_level}_from_path` properties to the `Requirement` class
- feat(core): add properties to get parents and siblings of a given profile
- feat(core): add getter for sibling profiles
- feat(core): mark a requirement as overridden if all checks are overridden
- feat(core): do not notify events of overridden requirements
- feat(core): improve detection of check overrides
- feat(core): extend the check model to support multiple overrides
- feat(cli): support `profiles-path` override on `profiles` subcommand
- feat(cli): show multiple check overrides
- feat(cli): allow configuring the list of checks to skip via CLI

### 🔧 Changed

- build: rename package to `roc-validator`
- build: update package version number
- refactor(core): use the `severity` property to denote the severity level of a Python requirement
- refactor(cli): remove short option for `profiles_path`
- refactor(profiles/ro-crate): move WebDataEntity shapes
- refactor(shacl): restructure the logic to set/get requirement level on SHACL checks
- refactor(core): update `Requirement.level` definition
- refactor(core): update the requirements loading process
- refactor(shacl): set the conforms property to be computed based on the presence of issues
- refactor(core): fix the sorting criteria of the requirements
- refactor(core): safer way to add candidate profiles
- refactor(cli): fix output of `profiles describe` command

### 🐛 Fixed

- fix(shacl): fix property getter
- fix(profiles/ro-crate): fix severity of WebDataEntity shapes
- fix(shacl): fix the override of the base method
- fix(shacl): always parse the result graph
- fix(profiles/ro-crate): fix mismatch in the requirement level
- fix(core): fix LevelCollection getter
- fix(core): wrong property name
- fix(core): properly initialize `PyRequirement` instances
- fix(shacl): use the shape description
- fix(shacl): fix condition to print the mismatch warning
- fix(core): fix in progress for detecting overrides
- fix(profiles/ro-crate): fix inconsistent severity level
- fix(shacl): report a generic error when the metadata is invalid

### 📚 Documentation

- docs(core): add package description
- docs(readme): update testing status and license badges

### ⚡ Performance

- perf(shacl): filter shapes based on the requirement level
- perf(shacl): set the check severity based on the declared value, or infer it from the path
- perf(shacl): allow to get declared `severity` of a Shape Node

## [0.1.2] - 2024-09-19

### ✨ Added

- feat(core): declare package version
- feat(utils): enhance version detection: take Git repository state into account
- feat(ci): set up automatic release process
- feat: add minimal cli entrypoint
- feat(srv): add validation services
- feat: add models
- feat: add utils module
- feat: initial minimal shapes

### 🔧 Changed

- build: configure the `rocrate-validator` script
- build(core): update Python packages
- build(dep): add click dependency
- build(dep): add pyshacl dependency
- build(dep): add rdflib dependency
- build: init poetry project
- refactor: move code to the rocrate-validator folder
- refactor: move ttl file
- refactor: move code to the src folder
- refactor(cli): disable ontologies parameter
- refactor(utils): generic function to load graphs from paths

## [0.1.1] - 2024-02-20

### ✨ Added

- Initial release
- feat: add minimal cli entrypoint
- feat(srv): add validation services
- feat: add models
- feat: add utils module
- feat: initial minimal shapes

### 🔧 Changed

- build: configure the `rocrate-validator` script
- build(core): update Python packages
- build(dep): add click dependency
- build(dep): add pyshacl dependency
- build(dep): add rdflib dependency
- build: init poetry project
- refactor: move code to the rocrate-validator folder
- refactor: move ttl file
- refactor: move code to the src folder
- refactor(cli): disable ontologies parameter
- refactor(utils): generic function to load graphs from paths
