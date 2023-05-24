import shutil
import os.path

archive_filepath = "./archives"
raw_filepath = "./raw"

if __name__ == '__main__':
    for path in [archive_filepath, raw_filepath]:
        for item in os.listdir(path):
            ym = item[:7].replace('-', '')
            new_path = f"{path}/{ym}"
            if not os.path.exists(new_path):
                os.makedirs(new_path)
            shutil.move(f"{path}/{item}", f"{new_path}/{item}")
