#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#
# Copyright 2016, 2017 Guenter Bartsch
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
# another more advanced demonstration program for kaldiasr online nnet3 
# decoding where we stream audio frames incrementally to two decoder instances
# running on the same model simultaneously
#

import sys
import os
import wave
import struct
import numpy as np

from time import time

from kaldiasr.nnet3 import KaldiNNet3OnlineModel, KaldiNNet3OnlineDecoder

if __name__ == "__main__":

    MODELDIR    = 'data/models/kaldi-nnet3-voxforge-de-latest'
    MODEL       = 'nnet_tdnn_a'
    WAVFILE1    = 'data/single.wav'
    WAVFILE2    = 'data/gsp1.wav'

    print '%s loading model...' % MODEL
    kaldi_model = KaldiNNet3OnlineModel (MODELDIR, MODEL)
    print '%s loading model... done.' % MODEL

    decoder1 = KaldiNNet3OnlineDecoder (kaldi_model)
    decoder2 = KaldiNNet3OnlineDecoder (kaldi_model)
    
    time_start = time()

    wavf1 = wave.open(WAVFILE1, 'rb')
    wavf2 = wave.open(WAVFILE2, 'rb')

    # process files in 250ms chunks

    chunk_frames = 250 * wavf1.getframerate() / 1000
    tot_frames1   = wavf1.getnframes()
    tot_frames2   = wavf2.getnframes()

    num_frames1 = 0
    num_frames2 = 0
    while num_frames1 < tot_frames1 or num_frames2 < tot_frames2:

        if num_frames1 < tot_frames1:
            finalize = False
            if (num_frames1 + chunk_frames) < tot_frames1:
                nframes = chunk_frames
            else:
                nframes = tot_frames1 - num_frames1
                finalize = True

            frames = wavf1.readframes(nframes)
            num_frames1 += nframes
            samples = struct.unpack_from('<%dh' % nframes, frames)

            decoder1.decode(wavf1.getframerate(), np.array(samples, dtype=np.float32), finalize)

            print "decoder1: %6.3fs: %5d frames (%6.3fs) decoded." % (time()-time_start, num_frames1, float(num_frames1) / float(wavf1.getframerate()) )

        if num_frames2 < tot_frames2:
            finalize = False
            if (num_frames2 + chunk_frames) < tot_frames2:
                nframes = chunk_frames
            else:
                nframes = tot_frames2 - num_frames2
                finalize = True

            frames = wavf2.readframes(nframes)
            num_frames2 += nframes
            samples = struct.unpack_from('<%dh' % nframes, frames)

            decoder2.decode(wavf2.getframerate(), np.array(samples, dtype=np.float32), finalize)

            print "decoder2: %6.3fs: %5d frames (%6.3fs) decoded." % (time()-time_start, num_frames2, float(num_frames2) / float(wavf2.getframerate()) )

    wavf1.close()
    wavf2.close()

    s, l = decoder1.get_decoded_string()
    print
    print "*****************************************************************"
    print "** DECODER 1"
    print "**", WAVFILE1
    print "**", s
    print "** %s likelihood:" % MODEL, l
    print "*****************************************************************"
    print

    s, l = decoder2.get_decoded_string()
    print
    print "*****************************************************************"
    print "** DECODER 2"
    print "**", WAVFILE2
    print "**", s
    print "** %s likelihood:" % MODEL, l
    print "*****************************************************************"
    print
    print "%s decoding took %8.2fs" % (MODEL, time() - time_start )


