"""Translate pinned render graphs for the frame-exact render change only."""


def frame_exact_graph(graph, cuts):
    """Map old video pieces and the speed tail; preserve every other byte.

    The frame-exact render change conforms before trimming by frame index and
    adds lookahead at speed, then caps the joined video at the cut list's total.
    Spell out the substitution independently of the renderer under test.
    """
    fps, speed, segments = cuts["fps"], cuts["speed"], cuts["segments"]
    for i, segment in enumerate(segments):
        start, end = segment["src_in_f"], segment["src_out_f"]
        old = ("trim=start=%r:end=%r,setpts=PTS-STARTPTS,fps=%r,trim=end_frame=%d[v%d];"
               % (start / fps, end / fps, fps, end - start, i))
        new = ("fps=%r:start_time=0,trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS[v%d];"
               % (fps, start, end, i))
        if graph.count(old) != 1:
            raise ValueError("expected exactly one pinned video piece for segment %d" % i)
        graph = graph.replace(old, new, 1)
    speed_filters = "setpts=PTS/%r,fps=%r," % (speed, fps) if abs(speed - 1.0) >= 1e-9 else ""
    old = "\n[vc]" + speed_filters
    new = ("\n[vc]" + ("tpad=stop_mode=clone:stop=1," if speed_filters else "") + speed_filters
           + "trim=end_frame=%d," % segments[-1]["out_out_f"])
    if graph.count(old) != 1:
        raise ValueError("expected exactly one pinned video tail")
    return graph.replace(old, new, 1)
