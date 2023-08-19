import os
import datetime
import pathlib

today = datetime.date.today()
year = today.year
month = today.month
day = today.day

TEST=False

def filecheck(file_name) -> bool:
    path = pathlib.Path('./') / str(year) / str(month) / str(day) / file_name
    if TEST:
        print(f"path {path.as_posix()} exists:", path.exists())
    return path.exists()

if __name__ == "__main__":
    flag = filecheck("free.json") and filecheck("paid.json")
    if os.getenv('CI', 'false') == 'true':
        os.system(f'echo "flag={str(flag)}" >> "$GITHUB_OUTPUT"')
