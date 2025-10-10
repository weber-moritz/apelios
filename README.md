This project will be head turning.
Its to contol moving heads (like the Clay Paky Alpha Profile 1500) with a steam deck.

# USAGE
use `python -m src.apelios.main` to execute the project
## Structure:
I use VScode to write the code.
If i want to test stuff on the hardware, i use ssh to connect to the steam deck with vscode and code there.
## Code:
- `scripts` is for deployment, compiling and stuff like that
- `src` contains the module that is apelios. this is a self executable module 


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
`pyhton3 -m apelios.main`
