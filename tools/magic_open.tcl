# Magic processes a startup script before other file arguments. Load explicitly
# so display commands always apply to the requested design, including in the GUI.
# The CLI supplies a basename and starts in the layout's directory.
load $env(BANDGAP_LAYOUT)
select top cell
expand
select clear
view
