# Copyright 2017 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path

from ament_flake8.main import main_with_errors
import pytest


@pytest.mark.flake8
@pytest.mark.linter
def test_flake8():
    config_file = Path(__file__).parent.parent / "setup.cfg"

    # Debug: Ensure the file exists and print its path
    assert config_file.is_file(), f"Config file not found at: {config_file}"

    # Debug: Print the config file being used
    print(f"Flake8 is using configuration file: {config_file}")

    # Run the actual linting test
    rc, errors = main_with_errors(argv=["--config", str(config_file)])
    assert rc == 0, "Found %d code style errors / warnings:\n" % len(errors) + "\n".join(errors)
