#
# Copyright 2015 MarkLogic Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# File History
# ------------
#
# Paul Hoehne       03/01/2015     Initial development
#

import os, sys, stat

"""
MarkLogic file classes
"""

def walk_directories(current_directory):
    """
    Recursively walk a directory returning all of the files found.
    """
    file_list = []
    for dir in os.listdir(current_directory):
        pathname = os.path.join(current_directory, dir)
        mode = os.stat(pathname).st_mode

        if stat.S_ISDIR(mode):
            file_list.extend(walk_directories(pathname))
        else:
            file_list.append({'filename': dir, 'partial-directory': pathname})
    return file_list
