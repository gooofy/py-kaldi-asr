#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#
# Copyright 2016, 2017, 2018 Guenter Bartsch
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# THIS CODE IS PROVIDED *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
# WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
# MERCHANTABLITY OR NON-INFRINGEMENT.
# See the Apache 2 License for the specific language governing permissions and
# limitations under the License.
#
#
# slightly more advanced demonstration program for kaldiasr online nnet3 
# decoding where we stream audio frames incrementally to the decoder
#

import sys
import os
import wave
import struct
import numpy as np

from time import time

from kaldiasr.nnet3 import KaldiNNet3OnlineModel, KaldiNNet3OnlineDecoder

MODELDIR    = 'data/models/kaldi-generic-en-tdnn_sp-latest'
# MODELDIR    = 'data/models/kaldi-generic-de-tdnn_sp-latest'
WAVFILE     = 'data/dw961.wav'
# WAVFILE     = 'data/fail1.wav'
# WAVFILE     = 'data/gsp1.wav'

print '%s loading model...' % MODELDIR
time_start = time()
kaldi_model = KaldiNNet3OnlineModel (MODELDIR, acoustic_scale=1.0, beam=7.0, frame_subsampling_factor=3)
print '%s loading model... done, took %fs.' % (MODELDIR, time()-time_start)

print '%s creating decoder...' % MODELDIR
time_start = time()
decoder = KaldiNNet3OnlineDecoder (kaldi_model)
print '%s creating decoder... done, took %fs.' % (MODELDIR, time()-time_start)

time_start = time()

if decoder.decode_wav_file(WAVFILE):

    s, l = decoder.get_decoded_string()

    print
    print "*****************************************************************"
    print "**", WAVFILE
    print "**", s
    print "** %s likelihood:" % MODELDIR, l
    print "*****************************************************************"
    print
    print "%s decoding took %8.2fs" % (MODELDIR, time() - time_start )

else:

    print "***ERROR: decoding of %s failed." % WAVFILE

