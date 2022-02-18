import subprocess
import logging

def check_package(pkg_name:str) -> bool:
    is_present = subprocess.run(
            ["dpkg", "-s", pkg_name], stdout=subprocess.DEVNULL)
    # is_present = 0 if pkg is present, is_present = 1 if is not
    # installed so we need to "invert" the process exit code
    is_present = not is_present.returncode
    logging.info(pkg_name + " found" if is_present else " not available.")
    return is_present