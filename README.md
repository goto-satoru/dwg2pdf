# Custom DWG Converter

[![Build Windows Executable](https://github.com/goto-satoru/dwg-converter/actions/workflows/python-exe.yml/badge.svg)](https://github.com/goto-satoru/dwg-converter/actions/workflows/python-exe.yml)

## Prerequisites

- Cognite Data Fusion(CDF) tenant
- client ID/secret of Enterprise Application of Microsoft Entra ID, which is associated with CDF
- [Poetry](https://python-poetry.org/docs/)

## ToDo in development environment

- use Python 3.11

```
poetry env use 3.11
```

- install dependnt packages

```
poetry install
```


- remove status.json form 1st time bulk conversion

- run DWG Converter on macOS / Linux

```
poetry run box_extractor
```

- Build executable(.exe) on Windows (will be built in GitHub Actions)

```
poetry run pyinstaller windows_exe.spec
```

delete old artifacts if you have only 500 MB storage on GitHub
