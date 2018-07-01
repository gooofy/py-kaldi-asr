#!/usr/bin/env python3
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
# very simple single WAV file speech recognition (decoding) example 
#
# Python 3 version
#

from kaldiasr.nnet3 import KaldiNNet3OnlineModel, KaldiNNet3OnlineDecoder

MODELDIR    = 'data/models/kaldi-generic-en-tdnn_sp-latest'
# MODELDIR    = 'data/models/kaldi-generic-de-tdnn_sp-latest'
WAVFILE     = 'data/dw961.wav'
# WAVFILE     = 'data/fail1.wav'
# WAVFILE     = 'data/gsp1.wav'

kaldi_model = KaldiNNet3OnlineModel (MODELDIR, acoustic_scale=1.0, beam=7.0, frame_subsampling_factor=3)
decoder     = KaldiNNet3OnlineDecoder (kaldi_model)

if decoder.decode_wav_file(WAVFILE):

    s, l = decoder.get_decoded_string()

    print()
    print("*****************************************************************")
    print("** %s" % WAVFILE)
    print("** %s" % s)
    print("** %s likelihood: %f" % (MODELDIR, l))
    print("*****************************************************************")
    print()

else:

    print("***ERROR: decoding of %s failed." % WAVFILE)

