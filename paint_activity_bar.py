# ----- imports -----

# native
import os
import subprocess
from datetime import datetime

# third party
from dotenv import load_dotenv

# ----- globals -----

# debug
debug = True

# credentials
load_dotenv()
dummy_repo_path = os.getenv("dummy_repo_path")
start_date = os.getenv("start_date")

# ----- helper functions -----

def date_string_to_timestamp(date_string):
    dt_object = datetime.strptime(date_string, "%Y-%m-%d")
    timestamp = dt_object.timestamp()
    return timestamp

def timestamp_to_date_string(timestamp):
    dt_object = datetime.fromtimestamp(timestamp)
    date = dt_object.strftime("%Y-%m-%d")
    return date

def run_bash(commands):
    result = subprocess.run(commands, shell=True, capture_output=True, text=True)
    output = result.stdout
    if (debug):
        print(commands)
        print(output)
    return output

def pull_dummy_repo():
    commands = \
    f"""
        cd {dummy_repo_path}
        git pull
    """
    run_bash(commands)

def is_readme_created():
    readme_path = dummy_repo_path + '/README.md'
    return os.path.exists(file_path)

def create_readme():
    assert(os.path.exists('readme_template.md'))
    commands = \
    f"""
        cp readme_template.md {dummy_repo_path}/README.md
    """
    run_bash(commands)

def get_commit_timeline():
    pass #TODO

# ----- main -----

def main():
    pull_dummy_repo()

    # start date
    dt_object = datetime.strptime(start_date, "%Y-%m-%d")

if __name__ == '__main__':
    main()
