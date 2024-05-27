# SQLite

## Installation

To install the SQLite library, follow the steps for your system:

### Windows

1. **Download SQLite:**
   Go to the [SQLite download page](https://www.sqlite.org/download.html) and
   download the precompiled binaries for Windows. Download the following files:
   - sqlite-tools-win32-x86-XXXXXX.zip (contains the SQLite command-line tools)
   - sqlite-dll-win32-x86-XXXXXX.zip or sqlite-dll-win64-x64-XXXXXX.zip
     (contains the SQLite DLL)

2. **Extract the Files:**
   Extract the contents of these ZIP files to a directory of your choice, for example, `C:\sqlite`.

3. **Add SQLite to PATH:**
   Add the directory containing `sqlite3.exe` to your system's PATH environment variable:
   - Open the Start Menu, search for "Environment Variables", and select "Edit the system environment variables".
   - In the System Properties window, click on the "Environment Variables" button.
   - In the Environment Variables window, find the "Path" variable in the "System variables" section and click "Edit".
   - Click "New" and add the path to the directory where you extracted the SQLite binaries, for example, `C:\sqlite`.
   - Click "OK" to close all windows.

4. **Verify the Installation:**
   Open a new Command Prompt window and run:
   ```sh
   sqlite3 --version
   ```
   This should print the version of SQLite installed.

### macOS

1. **Install Homebrew:**
   Homebrew is a popular package manager for macOS. If you don't have Homebrew
   installed, you can install it by running the following command in your
   terminal:
   ```sh
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install SQLite:**
   Once Homebrew is installed, you can install SQLite by running:
   ```sh
   brew install sqlite3
   ```

3. **Verify the Installation:**
   After the installation is complete, you can verify that SQLite is installed
   correctly by running:
   ```sh
   sqlite3 --version
   ```
   This should print the version of SQLite installed.

4. **Reinstall Python:**
   If Python was installed before SQLite, you might need to reinstall Python to
   ensure it picks up the SQLite libraries. If you use `pyenv`, you can
   reinstall Python as follows:
   ```sh
   pyenv uninstall <your-python-version>
   pyenv install <your-python-version>
   ```
   Replace `<your-python-version>` with the specific version of Python you are
   using.

### Linux

To install SQLite on (Ubuntu) Linux, you can follow these steps:

1. **Update package list**:
   ```sh
   sudo apt update
   ```

2. **Install SQLite**: SQLite can now be installed by running:
   ```sh
   sudo apt install sqlite3
   ```
3. **Verify installation**: Once the installation is complete, you can verify
   the installation by checking the software’s version:
   ```sh
   sqlite3 --version
   ```
   This will output the version of SQLite installed on your system.

## Verify SQLite Support in Python

   After installing SQLite, you should verify that SQLite works in Python.

   Open a Python shell (by typing `python` in a terminal) and try importing the
   `sqlite3` module:

   ```python
   import sqlite3
   print(sqlite3.version)
   ```

   If no errors are encountered, SQLite is ready for use with Python.
