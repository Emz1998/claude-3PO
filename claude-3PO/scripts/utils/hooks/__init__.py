"""utils.hooks — dispatcher-side orchestration helpers, one submodule per hook.

Each submodule is named after the Claude Code hook it serves and exports the
helpers the corresponding ``dispatchers/<name>.py`` entrypoint delegates to.
Keeps dispatcher files down to ``main()`` + thin stdin/exit plumbing.
"""
