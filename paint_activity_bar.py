# ----- imports -----

# native
import os
import re
import subprocess
from datetime import datetime, timedelta

# third party
from dotenv import load_dotenv
import numpy as np
from PIL import Image

# ----- globals -----

# debug
debug = False

# parameters
load_dotenv()
dummy_repo_path = os.path.expanduser(os.getenv("dummy_repo_path"))
start_date_str = os.getenv("start_date")
start_date = None
end_date_str = os.getenv("end_date")
end_date = None
reference_date_str = os.getenv("reference_date")
reference_date = None
min_commit_count = int(os.getenv("min_commit_count"))
max_commit_count = int(os.getenv("max_commit_count"))
patterns_folder_path = os.path.expanduser(os.getenv("patterns_folder_path"))
pattern_name = os.getenv("pattern_name")
pattern_file_name = os.getenv("pattern_file_name")

# program
readme_template_path = "./readme_template.md"
timeline_start_marker = "[//]: # (COMMIT_TIMELINE_START)"
timeline_end_marker = "[//]: # (COMMIT_TIMELINE_END)"
timeline_header_lines = ["| Date (YYYY-MM-DD) | Percent |                                             Colour                                             | Commits Done | Target Commits |", "| :---------------: | :-----: | :--------------------------------------------------------------------------------------------: | :----------: | :------------: |"]

# github
low_color = (14, 68, 41)   #0e4429
high_color = (56, 211, 83) #39d353

# pattern
pattern = []
pattern_pixel_count = 0

# ----- classes -----

class Timeline_entry:
    def __init__(self, date, commit_percentage, commit_count, target_commit_count):
        if type(date) == str:
            date = datetime_string_to_object(date)
        self.date = date
        self.commit_percentage = commit_percentage
        self.commit_count = commit_count
        self.target_commit_count = target_commit_count
        # self.target_commit_count = get_target_commit_count_from_percentage(self.commit_percentage)

    def __str__(self):
        date_string = datetime_object_to_string(self.date)
        color_hex = get_commit_percentage_color(self.commit_percentage)
        entry = ""
        entry += f"| {date_string}" + " " * 8
        entry += f"| `{self.commit_percentage}%`" + " " * (5 - len(str(self.commit_percentage)))
        entry += f"| <img src=\"https://placehold.co/15x15/{color_hex}/{color_hex}.png\" alt=\"#{color_hex}\" height=\"12\" /> `#{color_hex}` "
        entry += f"| {self.commit_count}" + " " * (13 - len(str(self.commit_count)))
        entry += f"| {self.target_commit_count}" + " " * (15 - len(str(self.target_commit_count))) + "|"
        return entry

# ----- helper functions -----

def datetime_string_to_object(date_string):
    dt_object = datetime.strptime(date_string, "%Y-%m-%d")
    return dt_object

def datetime_object_to_string(dt_object):
    date = dt_object.strftime("%Y-%m-%d")
    return date

def run_bash(commands):
    result = subprocess.run(commands, shell=True, capture_output=True, text=True)
    output = result.stdout
    error = result.stderr
    if (debug):
        print(commands)
        print(output)
        print(error)
    return output, error

def pull_dummy_repo():
    commands = \
    f"""
        cd {dummy_repo_path}
        git pull
    """
    output, error = run_bash(commands)
    return ('fatal' not in error.strip())

def push_dummy_repo(date = None, commit_message = "auto"):
    date_param = ""
    if date is not None:
        date_param = f"--date {date.isoformat()}"
    commands = \
    f"""
        cd {dummy_repo_path}
        git add .
        git commit -am \"{commit_message}\" {date_param}
        git push
    """
    output, error = run_bash(commands)
    return ('fatal' not in error.strip())

def copy_file_to(src, trg):
    assert(os.path.exists(src))
    command = f"cp {src} {trg}"
    return run_bash(command)

def parse_dummy_readme(readme_path):
    # variables to return
    starting_lines = []
    timeline_entries = []
    ending_lines = []

    # process lines
    timeline_markers_count = 0
    with open(readme_path, 'r') as file:
        for line in file:
            clean_line = line.strip()

            # detect, count and skip markers
            if clean_line == timeline_start_marker or clean_line == timeline_end_marker:
                timeline_markers_count += 1
                continue
            
            # process line
            if timeline_markers_count == 0:
                starting_lines.append(line)
            elif timeline_markers_count == 1:
                # skip header lines and empty lines
                if clean_line in timeline_header_lines or clean_line == "":
                    continue
                timeline_entries.append(parse_timeline_entry(clean_line))
            elif timline_markers_count == 2:
                ending_lines.append(line)
            else:
                assert(False and "More timeline markers than expected!")

    return starting_lines, timeline_entries, ending_lines

def write_dummy_readme(readme_path, starting_lines, timeline_entries, ending_lines):
    with open(readme_path, "w") as file:
        file.writelines(starting_lines)
        for line in [timeline_start_marker, "",  *timeline_header_lines]:
            file.write(line + '\n')
        for entry in timeline_entries:
            file.write(str(entry) + '\n')
        file.writelines(["\n", timeline_end_marker, *ending_lines])

def rgb_to_hex(rgb):
    hex = "{:02x}{:02x}{:02x}".format(*rgb)
    return hex

def load_image(image_path):
    pixel_percentage = None
    with Image.open(image_path) as img:
        # convert to greyscale
        img = img.convert("L")
        
        # resize to a height of seven pixels
        target_height = 7
        width_percent = (target_height / float(img.size[1]))
        new_width = round((float(img.size[0]) * float(width_percent)))
        img = img.resize((new_width, target_height), Image.LANCZOS)

        # get pixel values
        pixels = list(img.getdata())

        # rescale colours
        max_pixel_value = max(pixels)
        min_pixel_value = min(pixels)
        pixels = [(pixel - min_pixel_value) / (max_pixel_value - min_pixel_value) * 255 for pixel in pixels]

        # place values as percetages in a 2d-list
        pixel_percentages = [[round(pixel / 255 * 100) for pixel in pixels[i : i + img.width]] for i in range(0, len(pixels), img.width)]
        assert(len(pixel_percentages) == 7 and "Pattern after rescaling is still not 7 pixels high!")
    return pixel_percentages

def get_pattern_pixel_percentage(pixel_index):
    return pattern[pixel_index % 7][pixel_index // 7]

def get_commit_percentage_color(percent):
    low_color_np = np.array(low_color)
    high_color_np = np.array(high_color)
    interpolated_color_np = low_color_np + (high_color_np - low_color_np) * (percent / 100)
    color = tuple(map(int, interpolated_color_np))
    return rgb_to_hex(color)

def get_target_commit_percentage_at(current_date):
    days_delta = (current_date - reference_date).days
    assert(days_delta >= 0 and "Date can not be before reference!")
    pixel_index = days_delta % pattern_pixel_count
    pixel_percentage = get_pattern_pixel_percentage(pixel_index)
    return pixel_percentage

def get_target_commit_count_from_percentage(percent):
    return min_commit_count + int((max_commit_count - min_commit_count) * (percent / 100))

def parse_timeline_entry(line):
    # match
    pattern = r"\| (\S*) *\| `(\d+)%` *\|.*\| (\d+) *\| (\d+) *\|"
    match = re.search(pattern, line)
    assert(match and "deformed commit line")

    # get matchin groups
    date = match.group(1)
    commit_percentage = int(match.group(2))
    commit_count = int(match.group(3))
    target_commit_count = int(match.group(4))

    # create and return the timeline entry object
    timeline_entry = Timeline_entry(date, commit_percentage, commit_count, target_commit_count)
    assert(commit_count <= timeline_entry.target_commit_count and "Faulty dummy readme, too many commits in one of the days, please recreate the dummy repo!")
    return timeline_entry

def next_day(dt):
    return dt + timedelta(days=1)

def today():
    current_datetime = datetime.now()
    current_date = current_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    return current_date

def mend_next_commit_gap(timeline_entries):
    current_date = start_date
    entry_index = 0
    while entry_index < len(timeline_entries):
        timeline_entry = timeline_entries[entry_index]
        if current_date < timeline_entry.date:
            target_commit_percentage = get_target_commit_percentage_at(current_date)
            target_commit_count = get_target_commit_count_from_percentage(target_commit_percentage)
            new_entry = Timeline_entry(current_date, target_commit_percentage, 1, target_commit_count)
            timeline_entries.insert(entry_index, new_entry)
            return False, current_date, timeline_entries
        elif current_date == timeline_entry.date:
            # check new tragets
            target_commit_percentage = get_target_commit_percentage_at(current_date)
            target_commit_count = get_target_commit_count_from_percentage(target_commit_percentage)
            assert(timeline_entry.commit_count <= target_commit_count and "Too many commits already done in one of the days, please recreate the dummy repo!")

            if timeline_entry.commit_count < target_commit_count:
                modified_entry = Timeline_entry(
                        current_date,
                        target_commit_percentage,
                        timeline_entry.commit_count + 1,
                        target_commit_count
                )
                timeline_entries[entry_index] = modified_entry
                return False, current_date, timeline_entries
        else:
            timeline_entries.pop(entry_index)
            continue

        current_date = next_day(current_date)
        entry_index += 1
    
    # if next entry is not beyond end date
    if current_date <= end_date:
        target_commit_percentage = get_target_commit_percentage_at(current_date)
        target_commit_count = get_target_commit_count_from_percentage(target_commit_percentage)
        timeline_entries.append(Timeline_entry(current_date, target_commit_percentage, 1, target_commit_count))
        return False, current_date, timeline_entries
    # if all commits done including one at end date
    else:
        return True, None, timeline_entries

# ----- main -----

def setup():
    global start_date
    global end_date
    global reference_date
    global pattern
    global pattern_pixel_count

    # turn date strings to dates
    start_date = datetime_string_to_object(start_date_str)
    end_date = datetime_string_to_object(end_date_str)
    reference_date = datetime_string_to_object(reference_date_str)

    # adjust reference date to be a sunday
    reference_weekday = reference_date.weekday()
    days_delta = (reference_weekday + 1) % 7
    reference_date = reference_date - timedelta(days=days_delta)

    # load pattern
    pattern_image_path = os.path.join(patterns_folder_path, pattern_name, pattern_file_name)
    assert(os.path.exists(pattern_image_path) and f"No pattern with this name found!")
    pattern = load_image(pattern_image_path)
    pattern_pixel_count = len(pattern) * len(pattern[0])
    
    # DEBUG: print pattern roughly
    # print('pattern:')
    # for i in range(7):
    #     for j in range(len(pattern[0])):
    #         c = 'x'
    #         if pattern[i][j] < 50:
    #             c = '.'
    #         print(c, end = "")
    #     print('')

def main():
    pulled = False
    while not pulled:
        pulled = pull_dummy_repo()
    readme_path = dummy_repo_path + '/README.md'
    if not os.path.exists(readme_path):
        print(f"Creating new dummy repo README.md at {readme_path}")
        copy_file_to(readme_template_path, readme_path)
    starting_lines, timeline_entries, ending_lines = parse_dummy_readme(readme_path)

    counter = 0
    while True:
        # next commit
        done, commit_date, new_timeline_entries = mend_next_commit_gap(timeline_entries)
        # terminate if no more commits to be done
        if done:
            break

        # do the commit
        print(f"[*] New commit at {datetime_object_to_string(commit_date)}")
        timeline_entries = new_timeline_entries
        write_dummy_readme(readme_path, starting_lines, timeline_entries, ending_lines)
        pushed = False
        while not pushed:
            pushed = push_dummy_repo(commit_date)

if __name__ == '__main__':
    setup()
    main()
