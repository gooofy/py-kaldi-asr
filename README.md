# py-kaldi-asr

Some simple wrappers around kaldi-asr intended to make using kaldi's (online, nnet3, chain)
decoders as convenient as possible. 

Target audience are developers who would like to use kaldi-asr as-is for speech
recognition in their application on GNU/Linux operating systems.

Constructive comments, patches and pull-requests are very welcome.

Getting Started
===============

We recommend using pre-trained modules from the [zamia-speech](http://zamia-speech.org/) project
to get started. There you will also find a tutorial complete with links to pre-built binary packages
to get you up and running with free and open source speech recognition in a matter of minutes:

[Zamia Speech Tutorial](https://github.com/gooofy/zamia-speech#get-started-with-our-pre-trained-models)

Example Code
------------

Simple wav file decoding:

```python
from kaldiasr.nnet3 import KaldiNNet3OnlineModel, KaldiNNet3OnlineDecoder

MODELDIR    = 'data/models/kaldi-generic-en-tdnn_sp-latest'
WAVFILE     = 'data/dw961.wav'

kaldi_model = KaldiNNet3OnlineModel (MODELDIR, acoustic_scale=1.0, beam=7.0, frame_subsampling_factor=3)
decoder     = KaldiNNet3OnlineDecoder (kaldi_model)

if decoder.decode_wav_file(WAVFILE):

    s, l = decoder.get_decoded_string()

    print
    print "*****************************************************************"
    print "**", WAVFILE
    print "**", s
    print "** %s likelihood:" % MODELDIR, l
    print "*****************************************************************"
    print

else:

    print "***ERROR: decoding of %s failed." % WAVFILE
```

Please check the examples directory for more example code.

Requirements
============

* Python 2.7 or 3.5
* NumPy
* Cython
* [kaldi-asr](http://kaldi-asr.org/ "kaldi-asr.org")

Setup Notes
===========

Source
------

At the time of this writing kaldi-asr does not seem to have an official way to
install it on a system. 

So, for now we will rely on pkg-config to provide LIBS and CFLAGS for compilation:
Create a file called `kaldi-asr.pc` somewhere in your `PKG_CONFIG_PATH` that provides
this information:

```bash
kaldi_root=/opt/kaldi

Name: kaldi-asr
Description: kaldi-asr speech recognition toolkit
Version: 5.2
Requires: atlas
Libs: -L${kaldi_root}/tools/openfst/lib -L${kaldi_root}/src/lib -lkaldi-decoder -lkaldi-lat -lkaldi-fstext -lkaldi-hmm -lkaldi-feat -lkaldi-transform -lkaldi-gmm -lkaldi-tree -lkaldi-util -lkaldi-matrix -lkaldi-base -lkaldi-nnet3 -lkaldi-online2 -lkaldi-cudamatrix -lkaldi-ivector -lfst
Cflags: -I${kaldi_root}/src  -I${kaldi_root}/tools/openfst/include
```

make sure `kaldi_root` points to wherever your kaldi checkout lives in your filesystem.

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

