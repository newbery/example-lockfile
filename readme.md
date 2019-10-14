# lockfile.py

Example code for discussion and presentation purposes.

I had a requirement to download and process very large files on demand where
it was likely that multiple web requests to process the same file would arrive
nearly simultaneously. Since these were long-lived operations, the processing
was performed asynchronously and the user presented with non-blocking progress
updates.

To avoid duplicative work and file write collisions, I wrote this simple file
locking library to queue up the simultaneous requests.

The usage and software contract is reasonably well-documented in the tests module.
If anything is unclear, please feel free to ping me.
