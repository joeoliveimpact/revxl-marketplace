"""Read-only picture selection shared by Sound Board setup and page loads (stdlib only)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'editor-doctor/scripts'))
from hub_rows import cockpit_rules, stage_done  # noqa: E402


def _usable(path, reel):
    return (path.is_file() and '.partial' not in path.name.lower()
            and path.resolve().is_relative_to(reel.resolve()))


def find_picture(reel, video=None):
    """--video, else a preview newer than cut and completed Motion lock, then config/cut."""
    if video:
        return Path(video)
    cuts = [p for p in (reel / 'work/renders').glob('master-*.mp4') if _usable(p, reel)]
    cut = max(cuts, key=lambda p: p.stat().st_mtime_ns, default=None)
    since = cut.stat().st_mtime_ns if cut else 0
    selection = reel / 'motion-review-selection.json'
    if selection.is_file():
        # Use the Cockpit's actual Motion rule, including review freshness and explicit none.
        motion = next(s['rule'] for s in cockpit_rules()[0] if s['name'] == 'Motion')
        if stage_done(motion, {}, reel):
            since = max(since, selection.stat().st_mtime_ns)
    previews = [p for p in (reel / 'renders').glob('* Preview 720p - *.mp4')
                if _usable(p, reel) and p.stat().st_mtime_ns > since]
    if previews:
        return max(previews, key=lambda p: p.stat().st_mtime_ns)
    try:
        url = json.loads((reel / 'config.json').read_text(encoding='utf-8')).get('picture_url')
        configured = reel / url if url else None
        if (configured and _usable(configured, reel)
                and not configured.match('* Preview 720p - *.mp4')):
            return configured
    except (OSError, ValueError):
        pass
    return cut


def picture_label(video, explicit=False):
    if video.match('* Preview 720p - *.mp4'):
        return 'Playing your preview: ' + video.name
    if video.match('master-*.mp4'):
        return 'Playing the first cut' + ('' if explicit else ' (no preview yet)')
    return 'Playing ' + video.name
