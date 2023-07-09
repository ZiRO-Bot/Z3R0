"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from pathlib import Path

from single_source import get_version


pathToPyprojectDir = Path(__file__).parent.parent.parent
__version__ = get_version(__name__, pathToPyprojectDir, default_return=None)
