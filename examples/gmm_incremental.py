#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#
# Author: David Zurow, adapted from G. Bartsch
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
# slightly more advanced demonstration program for kaldiasr online gmm 
# decoding where we stream audio frames incrementally to the decoder
#

from __future__ import print_function

import sys
import os
import wave
import struct
import numpy as np

from time import time

from kaldiasr.gmm import KaldiGmmOnlineModel, KaldiGmmOnlineDecoder

# this is useful for benchmarking purposes
NUM_DECODER_RUNS = 1

# ../../training/kaldi_tmp/exp/
# |-- tri3b
# |   |-- graph
# |   |   |-- HCLG.fst
# |   |   |-- disambig_tid.int
# |   |   |-- num_pdfs
# |   |   |-- phones
# |   |   |   |-- align_lexicon.int
# |   |   |   |-- align_lexicon.txt
# |   |   |   |-- disambig.int
# |   |   |   |-- disambig.txt
# |   |   |   |-- optional_silence.csl
# |   |   |   |-- optional_silence.int
# |   |   |   |-- optional_silence.txt
# |   |   |   |-- silence.csl
# |   |   |   |-- word_boundary.int
# |   |   |   `-- word_boundary.txt
# |   |   |-- phones.txt
# |   |   `-- words.txt
# |-- tri3b_mmi_online
# |   |-- cmvn_opts
# |   |-- conf
# |   |   |-- mfcc.conf
# |   |   |-- online_cmvn.conf
# |   |   |-- online_decoding.conf
# |   |   `-- splice.conf
# |   |-- final.mat
# |   |-- final.mdl
# |   |-- final.oalimdl
# |   |-- final.rescore_mdl
# |   |-- fmllr.basis
# |   |-- global_cmvn.stats
# |   |-- phones.txt
# |   `-- splice_opts

MODELDIR    = '../../training/kaldi_tmp/exp/tri3b_mmi_online'
GRAPHDIR    = '../../training/kaldi_tmp/exp/tri3b'
WAVFILE     = 'data/dw961.wav'

print('%s loading model...' % MODELDIR)
time_start = time()
kaldi_model = KaldiGmmOnlineModel (MODELDIR, GRAPHDIR)
print('%s loading model... done, took %fs.' % (MODELDIR, time()-time_start))

print('%s creating decoder...' % MODELDIR)
time_start = time()
decoder = KaldiGmmOnlineDecoder (kaldi_model)
print('%s creating decoder... done, took %fs.' % (MODELDIR, time()-time_start))

for i in range(NUM_DECODER_RUNS):

    time_start = time()

    print('decoding %s...' % WAVFILE)
    wavf = wave.open(WAVFILE, 'rb')

    # check format
    assert wavf.getnchannels()==1
    assert wavf.getsampwidth()==2

    # process file in 250ms chunks

    chunk_frames = int(250 * wavf.getframerate() / 1000)
    tot_frames   = wavf.getnframes()

    num_frames = 0
    while num_frames < tot_frames:

        finalize = False
        if (num_frames + chunk_frames) < tot_frames:
            nframes = chunk_frames
        else:
            nframes = tot_frames - num_frames
            finalize = True

        frames = wavf.readframes(nframes)
        num_frames += nframes
        samples = struct.unpack_from('<%dh' % nframes, frames)

        decoder.decode(wavf.getframerate(), np.array(samples, dtype=np.float32), finalize)

        s, l = decoder.get_decoded_string()

        print("%6.3fs: %5d frames (%6.3fs) decoded. %s" % (time()-time_start, num_frames, float(num_frames) / float(wavf.getframerate()), s))

    wavf.close()

    s, l = decoder.get_decoded_string()
    print()
    print("*****************************************************************")
    print("**", WAVFILE)
    print("**", s)
    print("** %s likelihood:" % MODELDIR, l)

    time_scale = 0.01
    words, times, lengths = decoder.get_word_alignment()
    print("** word alignment: :")
    for i, word in enumerate(words):
        print('**   %f\t%f\t%s' % (time_scale * float(times[i]), time_scale*float(times[i] + lengths[i]), word))

    print("*****************************************************************")
    print()
    print("%s decoding took %8.2fs" % (MODELDIR, time() - time_start ))
