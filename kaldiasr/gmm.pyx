# distutils: language = c++
# distutils: sources = gmm.cpp

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

import cython
from libcpp.string cimport string
from libcpp.vector cimport vector
import numpy as np
cimport numpy as cnp
import struct
import wave
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
import subprocess
from cpython.version cimport PY_MAJOR_VERSION

cdef unicode _text(s):
    if type(s) is unicode:
        # Fast path for most common case(s).
        return <unicode>s

    elif PY_MAJOR_VERSION < 3 and isinstance(s, bytes):
        # Only accept byte strings as text input in Python 2.x, not in Py3.
        return (<bytes>s).decode('utf8')

    elif isinstance(s, unicode):
        # We know from the fast path above that 's' can only be a subtype here.
        # An evil cast to <unicode> might still work in some(!) cases,
        # depending on what the further processing does.  To be safe,
        # we can always create a copy instead.
        return unicode(s)

    else:
        raise TypeError("Could not convert to unicode.")

cdef extern from "gmm_wrappers.h" namespace "kaldi":

    cdef cppclass GmmOnlineModelWrapper:
        GmmOnlineModelWrapper() except +
        GmmOnlineModelWrapper(float, int, int, float, float, int, string, string, string, string, string) except +

    cdef cppclass GmmOnlineDecoderWrapper:
        GmmOnlineDecoderWrapper() except +
        GmmOnlineDecoderWrapper(GmmOnlineModelWrapper *) except +

        bint decode(float, int, float *, bint) except +

        void get_decoded_string(string &, float &) except +
        bint get_word_alignment(vector[string] &, vector[int] &, vector[int] &) except +

cdef class KaldiGmmOnlineModel:

    cdef GmmOnlineModelWrapper* model_wrapper
    cdef unicode                  modeldir, graph
    cdef object                   od_conf_f

    def __cinit__(self, object modeldir, 
                        object graph,
                        float  beam                     = 7.0, # nnet3: 15.0
                        int    max_active               = 7000,
                        int    min_active               = 200,
                        float  lattice_beam             = 8.0, 
                        float  acoustic_scale           = 1.0, # nnet3: 0.1
                        int    frame_subsampling_factor = 3,   # neet3: 1

                        int    num_gselect              = 5,
                        float  min_post                 = 0.025,
                        float  posterior_scale          = 0.1,
                        int    max_count                = 0,
                        int    online_ivector_period    = 10):

        self.modeldir         = _text(modeldir)
        self.graph            = _text(graph)

        cdef unicode config                = u'%s/conf/online_decoding.conf'             % self.modeldir
        cdef unicode word_symbol_table     = u'%s/graph/words.txt'                       % self.graph
        cdef unicode model_in_filename     = u'%s/final.mdl'                             % self.modeldir
        cdef unicode fst_in_str            = u'%s/graph/HCLG.fst'                        % self.graph
        cdef unicode align_lex_filename    = u'%s/graph/phones/align_lexicon.int'        % self.graph

        #
        # make sure all model files required exist
        #

        for conff in [config, word_symbol_table, model_in_filename, fst_in_str, align_lex_filename]:
            if not os.path.isfile(conff.encode('utf8')): 
                raise Exception ('%s not found.' % conff)
            if not os.access(conff.encode('utf8'), os.R_OK):
                raise Exception ('%s is not readable' % conff) 

        #
        # generate ivector_extractor.conf
        #

        self.od_conf_f = NamedTemporaryFile(prefix=u'py_online_decoding_', suffix=u'.conf', delete=True)
        # print(self.od_conf_f.name)
        with open(config) as file:
            for line in file:
                if re.search(r'=.*/.*', line):
                    self.od_conf_f.write(re.sub(r'=(.*)', lambda m: f"={self.modeldir}/{Path(*Path(m[1]).parts[2:])}", line).encode('utf8'))
                else:
                    self.od_conf_f.write(line.encode('utf8'))
        self.od_conf_f.flush()
        # subprocess.run(f"cat {self.od_conf_f.name}", shell=True)

        # self.ie_conf_f.write((u"--cmvn-config=%s/conf/online_cmvn.conf\n" % self.modeldir).encode('utf8'))
        # self.ie_conf_f.write((u"--ivector-period=%d\n" % online_ivector_period).encode('utf8'))
        # self.ie_conf_f.write((u"--splice-config=%s\n" % splice_conf_filename).encode('utf8'))
        # self.ie_conf_f.write((u"--lda-matrix=%s/extractor/final.mat\n" % self.modeldir).encode('utf8'))
        # self.ie_conf_f.write((u"--global-cmvn-stats=%s/extractor/global_cmvn.stats\n" % self.modeldir).encode('utf8'))
        # self.ie_conf_f.write((u"--diag-ubm=%s/extractor/final.dubm\n" % self.modeldir).encode('utf8'))
        # self.ie_conf_f.write((u"--ivector-extractor=%s/extractor/final.ie\n" % self.modeldir).encode('utf8'))
        # self.ie_conf_f.write((u"--num-gselect=%d\n" % num_gselect).encode('utf8'))
        # self.ie_conf_f.write((u"--min-post=%f\n" % min_post).encode('utf8'))
        # self.ie_conf_f.write((u"--posterior-scale=%f\n" % posterior_scale).encode('utf8'))
        # self.ie_conf_f.write((u"--max-remembered-frames=1000\n").encode('utf8'))
        # self.ie_conf_f.write((u"--max-count=%d\n" % max_count).encode('utf8'))
        # self.ie_conf_f.flush()

        #
        # instantiate our C++ wrapper class
        #

        self.model_wrapper = new GmmOnlineModelWrapper(beam, 
                                                         max_active, 
                                                         min_active, 
                                                         lattice_beam, 
                                                         acoustic_scale, 
                                                         frame_subsampling_factor, 
                                                         word_symbol_table.encode('utf8'), 
                                                         model_in_filename.encode('utf8'), 
                                                         fst_in_str.encode('utf8'), 
                                                         self.od_conf_f.name.encode('utf8'),
                                                         align_lex_filename.encode('utf8'))

    def __dealloc__(self):
        if self.od_conf_f:
            self.od_conf_f.close()
        if self.model_wrapper:
            del self.model_wrapper

cdef class KaldiGmmOnlineDecoder:

    cdef GmmOnlineDecoderWrapper* decoder_wrapper
    cdef object                     ie_conf_f

    def __cinit__(self, KaldiGmmOnlineModel model):

        #
        # instantiate our C++ wrapper class
        #

        self.decoder_wrapper = new GmmOnlineDecoderWrapper(model.model_wrapper)

    def __dealloc__(self):
        del self.decoder_wrapper

    def decode(self, samp_freq, cnp.ndarray[float, ndim=1, mode="c"] samples not None, finalize):
        return self.decoder_wrapper.decode(samp_freq, samples.shape[0], <float *> samples.data, finalize)

    def get_decoded_string(self):
        cdef string decoded_string
        cdef double likelihood=0.0
        self.decoder_wrapper.get_decoded_string(decoded_string, likelihood)
        return decoded_string.decode('utf8'), likelihood

    def get_word_alignment(self):
        cdef vector[string] words
        cdef vector[int] times
        cdef vector[int] lengths
        if not self.decoder_wrapper.get_word_alignment(words, times, lengths):
            return None
        return words, times, lengths

    #
    # various convenience functions below
    #

    def decode_wav_file(self, object wavfile):

        wavf = wave.open(wavfile, 'rb')

        # check format
        assert wavf.getnchannels()==1
        assert wavf.getsampwidth()==2
        assert wavf.getnframes()>0

        # read the whole file into memory, for now
        num_frames = wavf.getnframes()
        frames = wavf.readframes(num_frames)

        samples = struct.unpack_from('<%dh' % num_frames, frames)

        wavf.close()

        return self.decode(wavf.getframerate(), np.array(samples, dtype=np.float32), True)

