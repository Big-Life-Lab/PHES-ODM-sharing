# installation instructions

## system dependencies

- python >= 3.8
- pyenv (or python 3.8)

## development setup

```bash
# clone repo
git clone https://github.com/Big-Life-Lab/PHES-ODM-sharing odm-sharing
cd odm-sharing

# setup repo to run python 3.8
pyenv local 3.8

# create a virtual env for the repo
python -m venv .env

# activate the virtual env (must be done every time a new terminal is opened),
# or run .env/bin/pip and .env/bin/python directly
source .env/bin/activate

# make sure pip is up to date, and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# build and install the library in development mode
pip install -e .
```
