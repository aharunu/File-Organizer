# CS50 File Organizer

This script helps organize files in a specified directory by grouping them based on their file extension, name, or size. It also provides an option to undo the grouping (eject).

## Features

- **Group by Extension:** Organize files into folders based on their file extensions.
- **Group by Name:** Organize files into folders based on the first letter of their name.
- **Group by Size:** Organize files into folders based on their size categories.
- **Eject:** Undo the grouping by moving files back to the original directory.

## Usage

1. Clone or download the script to your local machine.
2. Ensure Python is installed on your system.
3. Run the script using the command:

   ```bash
   python your_script_name.py
   ```
4. Follow the on-screen prompts to select the desired operation.

## How It Works

### 1. Group by Extension
This option creates folders based on file extensions (e.g., `.txt`, `.jpg`) and moves the corresponding files into these folders. Directories within the specified path are moved into a folder named `Directory`.
### 2. Group by Name
This option creates folders based on the first letter of each file's name (e.g., `A`, `B`, `C`) and moves the files into these folders. Directories within the specified path are moved into a folder named `Directory`.
### 3. Group by Size
This option categorizes files into size-based folders:

* **Very Small (0-16 KB)**
* **Small (16 KB - 1 MB)**
* **Medium (1-128 MB)**
* **Large (128 MB - 1 GB)**
* **Very Large (1 GB+)**

Directories within the specified path are moved into a folder named `Directory`.

### 4. Eject
This option undoes the previous grouping by moving files back to the original directory and deleting the created folders.

## Example
Suppose you have a directory with the following files:
```
document.txt
photo.jpg
archive.zip
```
### Group by Extension
Running the script with the "Group by Extension" option will result in:
```
/txt/document.txt
/jpg/photo.jpg
/zip/archive.zip
```
### Group by Name
Running the script with the "Group by Name" option will result in:
```
/D/document.txt
/P/photo.jpg
/A/archive.zip
```
### Group by Size
Running the script with the "Group by Size" option will result in:
```
/Small (16 KB - 1 MB)/document.txt
/Medium (1-128 MB)/photo.jpg
/Small (16 KB - 1 MB)/archive.zip
```
### Eject
Running the script with the "Eject" option will move the files back to the original directory.
## Requirements
* Python 3.x
* `os` and `shutil` modules (included with Python standard library)
## Notes
* Ensure the script is run in a directory where you have read/write permissions.
* Be cautious when using the script as it moves files, which may affect their organization.
#### Video Demo:  <[CS50P Final Project](https://youtu.be/0MRLsabARyc)>