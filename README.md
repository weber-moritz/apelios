This project will be head turning.
Its to contol moving heads (like the Clay Paky Alpha Profile 1500) with a steam deck.

# USAGE
use `python -m apelios.main_orchestrator` to execute the project


## Python:
### Activate `venv`:
`source venv/bin/activate`
### Check if its working:
`which python` or `which pip` should point to this dir
### Create or extend requirements.txt for pip:
`pip freeze > requirements.txt` use `>` to overwrite and `>>` to append the file.
### Install packages from that list:
`pip install -r requirements.txt`
### Create `venv`:
`python3 -m venv venv`
### make it an editable module:
`nano pyproject.toml`
`pip install -e .`
`python3 -m apelios.main`
