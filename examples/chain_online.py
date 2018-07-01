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
# simple demonstration program for kaldiasr online nnet3-chain decoding
#

import sys
import os
import wave
import struct
import numpy as np

from time import time

from kaldiasr.nnet3 import KaldiNNet3OnlineModel, KaldiNNet3OnlineDecoder

# MODELDIR    = 'data/models/kaldi-generic-en-tdnn_sp-latest'
MODELDIR    = 'data/models/kaldi-generic-de-tdnn_sp-latest'
WAVFILES    = [ 'data/single.wav', 'data/gsp1.wav']

print '%s loading model...' % MODELDIR
kaldi_model = KaldiNNet3OnlineModel (MODELDIR)
print '%s loading model... done.' % MODELDIR

decoder = KaldiNNet3OnlineDecoder (kaldi_model)

for WAVFILE in WAVFILES:

    print 'decoding %s...' % WAVFILE
    time_start = time()
    if decoder.decode_wav_file(WAVFILE):
        print '%s decoding worked!' % MODELDIR

        s,l = decoder.get_decoded_string()
        print
        print "*****************************************************************"
        print "**", WAVFILE
        print "**", s
        print "** %s likelihood:" % MODELDIR, l

        time_scale = 0.01
        words, times, lengths = decoder.get_word_alignment()

        print "** word alignment: :"
        for i, word in enumerate(words):
            print '**   %f\t%f\t%s' % (time_scale * float(times[i]), time_scale*float(times[i] + lengths[i]), word)

        print "*****************************************************************"
        print

    else:
        print '%s decoding did not work :(' % MODELDIR

    print "%s decoding took %8.2fs" % (MODELDIR, time() - time_start )

