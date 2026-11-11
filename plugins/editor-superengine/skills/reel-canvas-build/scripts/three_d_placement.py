"""One data resolver for the 3D card envelope and face-safe choices."""
import placer


def card_box(spec, place):
    """Master-pixel visible envelope, including motion and decorative pixels.

    The glass slab is 720x216 at (150,402) or (150,1172), with z -140..0,
    tilt X 3..28 and Y -18..-2 degrees, and 24px of depth. A tight slab
    projection cannot bound the whole render: Quarks starts across 860px
    and h-30px, with sprites up to 26px, velocity and optical blur/bloom.
    Its conservative envelope is therefore the 900xh clipped canvas
    (h=500 or 360). Relative to the resting slab this reserves 90px per
    side and 142px/72px vertically; no extra margin outside the clip.
    Both CSS and WebGL are clipped there by #band's overflow/paint contain.
    """
    return tuple(spec["card"][place])


def clear_places(spec, head):
    """Unknown heads retain both choices; known heads protect eyes and mouth."""
    band = placer.face_band(head)
    return [place for place in ("top", "bottom")
            if band is None or not placer.hits(card_box(spec, place), band)]
