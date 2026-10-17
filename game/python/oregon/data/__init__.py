"""Every table the game uses, in one place.

Nothing here is logic. The contents come from the paper, from Appendix E (the saved
variable table ``VAR.BIN``), Appendix D (the dialogue records) and the BASIC source
itself where the data sits in DATA statements. Appendix F of the design notes, and
the transcription rules, both insist that tables do not end up scattered through
the code, so they live here and the game modules import them.

Two tables are checked against the paper by the test suite rather than merely
copied: the six climate strings, whose 144 character codes must agree with Table
13, and the landmark and segment tables, whose miles and speed bases must reproduce
the two route lengths the paper states -- 1,771 miles to The Dalles and 1,871 by the
Barlow Road.
"""

# Submodules are imported on demand rather than here, so that a module which
# needs only one table does not drag in the rest.
__all__ = ["climate", "dialogue", "goods", "hiscore", "illnesses", "landmarks",
           "rivers", "text"]
