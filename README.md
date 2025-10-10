This project will be head turning.
Its to contol moving heads (like the Clay Paky Alpha Profile 1500) with a steam deck.

# USAGE
## Structure:
I use VScode to write the code.
If i want to test stuff on the hardware, i use ssh to connect to the steam deck with vscode and code there.

## Python:
### Activate `venv`:
`source venv/bin/activate`
### Check if its working:
`which python` or `which pip` should point to this dir
### create or extend requirements.txt for pip:
`pip freeze > requirements.txt` use `>` to overwrite and `>>` to append the file.
### Create `venv`:
`python3 -m venv venv`