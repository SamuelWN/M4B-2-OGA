## M4B 2 OGA

A simple Python script to for converting an M4B audio file into an OGA file + accompanying metadata files.

Ouputs the following if available:
- Cue file
- Cover image
- Info (Summary, description, etc.)

### Note:

This script was developed with my own personal workflow in mind. Some behavior choices may not match your expectations/desired behavior.

If a file of the attempted output name already exists:
1. Assumes the OGA was made by a prior run:
  - Does not overwrite
  - Skips OGA generation
2. Assumes metadata files (`cover.jpg`, `info.txt`, `<FileName>.cue`) belong to the original M4B file
  - Does not overwrite
  - Saves the files with a suffixed filename
    - e.g. Given input `Example.m4b`: if `info.txt` exists, it saves to: `Example_info.txt` isntead.
