# Copyright 2015 Open Source Robotics Foundation, Inc.
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

from ament_pep257.main import main
import pytest


@pytest.mark.linter
@pytest.mark.pep257
def test_pep257():
    ignores = [
        "D100",
        "D101",
        "D102",
        "D103",
        "D104",
        "D105",
        "D106",
        "D107",
        "D202",  # No blank lines allowed after function docstring
        "D203",
        "D205",  # 1 blank line required between summary line and description
        "D212",
        "D400",  # First line should end with a period (not 'e')
        "D401",
        "D404",
        "D415",  # First line should end with a period, question mark, or exclamation point (not 'e')
    ]
    rc = main(argv=[".", "test", "--ignore"] + ignores)
    assert rc == 0, "Found code style errors / warnings"
