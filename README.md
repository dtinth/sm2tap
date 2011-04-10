sm2tap
======

StepMania to Tap Studio convertor. (Requires jailbroken iDevice)

Please read [my blog post](http://blog.dt.in.th/2011/02/sm2tap/) for more info.


Quick Start Guide
-----------------

1. In Tap Studio, create a __New Tap__ with the song you want.
2. Press __Record__, and record only one note and press __Stop__, __Go Back__ and __Save__.
3. In a file transfer program, navigate to Tap Studio's directory, then __Documents__, then __Local__.
4. Copy the __.tapd__ file that corresponds to your song into your Mac.
5. Open the Terminal.
6. `plutil -convert xml1 /path/to/your/song.tapd`
7. `python /path/to/convert.py /path/to/your/song.sm /path/to/your/song.tapd`
8. `plutil -convert binary1 /path/to/your/song.tapd`
9. Copy the `.tapd` file back.
10. Enjoy!
