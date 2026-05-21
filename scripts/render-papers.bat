@echo off
REM Regenerate PDFs from the three PPT-LAT-*.md papers.
REM Requires pandoc + xelatex on PATH (TeXLive 2023 or MiKTeX recent).
REM
REM Workspace alternative: use WSL or Linux shell with pandoc 2.x.
setlocal

set PAPERS=%~dp0..\papers
set DOCS=PPT-LAT-Theory PPT-LAT-Systems PPT-LAT-Roadmap

where pandoc >nul 2>&1 || (
    echo [render-papers] pandoc not on PATH.  Install pandoc + a TeX distro.
    echo                 Alternative: render from WSL ^(pandoc 2.x + xelatex^).
    exit /b 1
)

for %%D in (%DOCS%) do (
    echo === %%D ===
    pandoc "%PAPERS%\%%D.md" -o "%PAPERS%\%%D.pdf" ^
        --pdf-engine=xelatex ^
        -V geometry:margin=1in ^
        -V mainfont="DejaVu Sans" ^
        -V monofont="DejaVu Sans Mono" ^
        --highlight-style=tango ^
        -V colorlinks=true
)

echo RENDER_EXIT=%ERRORLEVEL%
endlocal
