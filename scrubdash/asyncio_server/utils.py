import os


def get_subdirectories(parent_directory):
    all_subdirs = [os.path.join(parent_directory, d)
                   for d in os.listdir(parent_directory)
                   if os.path.isdir(os.path.join(parent_directory, d))]

    return all_subdirs


def get_most_recent_subdirectory(directory_list):
    latest_subdir = max(directory_list, key=os.path.getmtime)

    return latest_subdir
