#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#
# Copyright 2016 Guenter Bartsch
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
# simple demonstration program for kaldisimple online nnet3 decoding
#

import sys
import os
import wave
import struct
import numpy as np

from time import time

from kaldisimple.nnet3 import KaldiNNet3OnlineDecoder

if __name__ == "__main__":

    MODELDIR    = 'data/models/kaldi-nnet3-voxforge-de-latest'
    # MODELS      = [ 'lstm_ld5', 'nnet_tdnn_a' ]
    MODELS      = [ 'nnet_tdnn_a' ]
    WAVFILES    = [ 'data/single.wav', 'data/gsp1.wav']

    for model in MODELS:

        print '%s loading model...' % model

        decoder = KaldiNNet3OnlineDecoder (MODELDIR, model)
        print '%s loading model... done.' % model
        
        for WAVFILE in WAVFILES:

            time_start = time()
            if decoder.decode_wav_file(WAVFILE):
                print '%s decoding worked!' % model

                s = decoder.get_decoded_string()
                print
                print "*****************************************************************"
                print "**", WAVFILE
                print "**", s
                print "** %s likelihood:" % model, decoder.get_likelihood()
                print "*****************************************************************"
                print

            else:
                print '%s decoding did not work :(' % model

            print "%s decoding took %8.2fs" % (model, time() - time_start )

