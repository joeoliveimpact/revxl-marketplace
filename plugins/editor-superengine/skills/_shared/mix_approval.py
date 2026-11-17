"""Content identity shared by the compositor and finished-render sound check."""
import hashlib
import json


SOUND_CHANGED = ("Your sound changed after you OK'd the preview. "
                 "Claude will remake the preview for you to OK.")


class MixApprovalError(ValueError):
    """The current mix is not the sound approved with the preview."""


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_approved_mix(reel, final):
    """Return the mix fingerprint, or refuse missing, legacy or different approvals."""
    try:
        ok = json.loads((reel / "work/render-ok.json").read_text(encoding="utf-8"))
        fingerprint = sha256(final)
    except (OSError, ValueError):
        raise MixApprovalError(SOUND_CHANGED) from None
    if not isinstance(ok, dict) or ok.get("mix_sha256") != fingerprint:
        raise MixApprovalError(SOUND_CHANGED)
    return fingerprint
