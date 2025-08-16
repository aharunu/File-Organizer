import os
import shutil

def main():
    path = "C:/Users/harun/Desktop/Eski Bilgisayar/Bitti/yen23/Bitti"
    path = path_verification(path)
    selection = input("Enter the operation you want to perform: \n1. Group by extension\n2. Group by name\n3. Group by size\n4. Eject Files\n")
    selection = case_selection(selection)
    dir_list = os.listdir(path)
    match(selection, dir_list, path)


def path_verification(path):
    if not os.path.isdir(path):
        raise FileNotFoundError(f"The directory '{path}' does not exist.")
    return path


def case_selection(selection):
    if not isinstance(selection, str):
        raise TypeError
    return selection


def match(selection, dir_list, path):
    match selection:
        case "1":
            extension_group(dir_list, path)
        case "2":
            name_group(dir_list, path)
        case "3":
            size_group(dir_list, path)
        case "4":
            eject(dir_list, path)


def extension_group(dir_list, path):
    for file in dir_list:
        extension = os.path.splitext(file)[1]
        extension_dir = os.path.join(path, extension.lstrip("."))

        if os.path.isdir(os.path.join(path, file)):
            dir = os.path.join(path, "Directory")
            if not os.path.exists(dir):
                os.makedirs(dir)
            shutil.move(os.path.join(path, file), os.path.join(dir, file))
        else:
            if not os.path.exists(extension_dir):
                os.makedirs(extension_dir)
            shutil.move(os.path.join(path, file), os.path.join(extension_dir, file))


def name_group(dir_list, path):
    for file in dir_list:
        new_path = os.path.join(path, file[0].capitalize())
        if os.path.isdir(os.path.join(path, file)):
            dir = os.path.join(path, "Directory")
            if not os.path.exists(dir):
                os.makedirs(dir)
            shutil.move(os.path.join(path, file), os.path.join(dir, file))
        else:
            if not os.path.exists(new_path):
                os.makedirs(new_path)
            shutil.move(os.path.join(path, file), os.path.join(new_path, file))


def size_group(dir_list, path):
    for file in dir_list:
        size = round(os.path.getsize(os.path.join(path, file)) / 1024)
        match size:
            case size if size == 0:
                size_dir = os.path.join(path, "Directory")
                if not os.path.exists(size_dir):
                    os.makedirs(size_dir)
                shutil.move(os.path.join(path, file), os.path.join(size_dir, file))
            case size if 0 < size < 16:
                size_dir = os.path.join(path, "Very Small (0-16 KB)")
                if not os.path.exists(size_dir):
                    os.makedirs(size_dir)
                shutil.move(os.path.join(path, file), os.path.join(size_dir, file))
            case size if 16 <= size < 1024:
                size_dir = os.path.join(path, "Small (16 KB - 1 MB)")
                if not os.path.exists(size_dir):
                    os.makedirs(size_dir)
                shutil.move(os.path.join(path, file), os.path.join(size_dir, file))
            case size if 1024 <= size < 1024 * 128:
                size_dir = os.path.join(path, "Medium (1-128 MB)")
                if not os.path.exists(size_dir):
                    os.makedirs(size_dir)
                shutil.move(os.path.join(path, file), os.path.join(size_dir, file))
            case size if 1024 * 128 <= size < 1024 * 1024:
                size_dir = os.path.join(path, "Large (128 MB - 1 GB)")
                if not os.path.exists(size_dir):
                    os.makedirs(size_dir)
                shutil.move(os.path.join(path, file), os.path.join(size_dir, file))
            case _:
                size_dir = os.path.join(path, "Very Large (1 GB+)")
                if not os.path.exists(size_dir):
                    os.makedirs(size_dir)
                shutil.move(os.path.join(path, file), os.path.join(size_dir, file))


def eject(dir_list, path): 
    for file in dir_list:
        new_path = os.path.join(path, file)
        if not os.path.isdir(new_path):
            continue

        for files in os.listdir(new_path):
            shutil.move(os.path.join(new_path, files), path)
        os.rmdir(new_path)


if __name__ == "__main__":
    main()