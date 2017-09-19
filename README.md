# py-kaldi-simple

Some simple wrappers around kaldi-asr intended to make using kaldi's (online)
decoders as convenient as possible. 

Target audience are developers who would like to use kaldi-asr as-is for speech
recognition in their application on GNU/Linux operating systems.

Constructive comments, patches and pull-requests are very welcome.

Example
=======

Simple wav file decoding:

```python
from kaldisimple.nnet3 import KaldiNNet3OnlineDecoder

MODELDIR    = 'data/models/kaldi-nnet3-voxforge-de-r20161117'
MODEL       = 'nnet_tdnn_a'
WAVFILE     = 'data/single.wav'

decoder = KaldiNNet3OnlineDecoder (MODELDIR, model)

if decoder.decode_wav_file(WAVFILE):

    print '%s decoding worked!' % model

    s = decoder.get_decoded_string()
    print
    print "*****************************************************************"
    print "**", s
    print "** %s likelihood:" % model, decoder.get_likelihood()
    print "*****************************************************************"
    print

else:
    print '%s decoding did not work :(' % model

```

Please check the examples directory for more example code.

Links
=====

* [Data / Models](http://goofy.zamia.org/voxforge/ "models")

* [Code](https://github.com/gooofy/py-kaldi-simple "github")

Requirements
============

*Note*: very incomplete.

* Python 2.7 with numpy, ...
* Cython
* kaldi-asr 5.1

Setup Notes
===========

At the time of this writing kaldi-asr does not seem to have an official way to
install it on a system. So, for now you will have to modify the supplied
Makefile and make sure the KALDI\_ROOT variable points to wherever your kaldi
checkout lives in your filesystem.

License
=======

My own code is Apache licensed unless otherwise noted in the script's copyright
headers.

Some scripts and files are based on works of others, in those cases it is my
intention to keep the original license intact. Please make sure to check the
copyright headers inside for more information.

Author
======

Guenter Bartsch <guenter@zamia.org>
Kaldi 5.1 adaptation contributed by mariasmo https://github.com/mariasmo

