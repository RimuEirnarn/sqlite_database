"""Used for debugging"""

from inspect import getouterframes, FrameInfo, Traceback

def _build_frame_str(frame: FrameInfo | Traceback):
    context_lines = '<no context>\n' if not frame.code_context else \
                    '\n>>> '.join(frame.code_context)
    lineno = frame.lineno or "<None>"
    filename = frame.filename or "<None>"
    function = frame.function or "<Callable()>"
    return f"""\
Trace at {lineno}, file {filename}, {function}
>>> {context_lines}"""

def map_frame(frame: Traceback) -> str:
    """Map a Taceback or FrameInfo to readable trace"""
    allframes = getouterframes(frame)
    allframes.reverse()

    builded = [_build_frame_str(frame) for frame in allframes]
    return ''.join(builded)

def map_frames(frames: list[FrameInfo | Traceback]):
    """Shorthand for alreadby built list of frames"""
    return ''.join((_build_frame_str(frame) for frame in frames))
