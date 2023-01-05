from pathlib import Path

from single_source import get_version


pathToPyprojectDir = Path(__file__).parent.parent.parent
__version__ = get_version(__name__, pathToPyprojectDir, default_return=None)
