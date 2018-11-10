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
import os, os.path
import re
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
        GmmOnlineModelWrapper(float, int, int, float, string, string, string, string) except +

    cdef cppclass GmmOnlineDecoderWrapper:
        GmmOnlineDecoderWrapper() except +
        GmmOnlineDecoderWrapper(GmmOnlineModelWrapper *) except +

        bint decode(float, int, float *, bint) except +

        void get_decoded_string(string &, float &) except +
        bint get_word_alignment(vector[string] &, vector[int] &, vector[int] &) except +

cdef class KaldiGmmOnlineModel:

    cdef GmmOnlineModelWrapper* model_wrapper
    cdef unicode                model_dir, graph_dir
    cdef object                 conf_file

    def __cinit__(self, object model_dir, 
                        object graph_dir,
                        float  beam                     = 7.0, # nnet3: 15.0
                        int    max_active               = 7000,
                        int    min_active               = 200,
                        float  lattice_beam             = 8.0): 

        self.model_dir = _text(model_dir)
        self.graph_dir = _text(graph_dir)

        cdef unicode config                = u'%s/conf/online_decoding.conf'             % self.model_dir
        cdef unicode word_symbol_table     = u'%s/graph/words.txt'                       % self.graph_dir
        cdef unicode fst_in_str            = u'%s/graph/HCLG.fst'                        % self.graph_dir
        cdef unicode align_lex_filename    = u'%s/graph/phones/align_lexicon.int'        % self.graph_dir

        #
        # make sure all model files required exist
        #

        for filename in [config, word_symbol_table, fst_in_str, align_lex_filename]:
            if not os.path.isfile(filename.encode('utf8')): 
                raise Exception ('%s not found.' % filename)
            if not os.access(filename.encode('utf8'), os.R_OK):
                raise Exception ('%s is not readable' % filename) 

        #
        # generate .conf file from existing one, modifying paths
        #

        self.conf_file = NamedTemporaryFile(prefix=u'py_online_decoding_', suffix=u'.conf', delete=True)
        # print(self.conf_file.name)
        with open(config) as file:
            for line in file:
                # modify any path, then write
                line = re.sub(r'=(.*/.*)',
                              lambda match: '=' + os.path.join(self.model_dir, '..', '..', match.group(1)),
                              line)
                self.conf_file.write(line.encode('utf8'))
        self.conf_file.flush()
        # subprocess.run('cat ' + self.conf_file.name, shell=True)

        #
        # instantiate our C++ wrapper class
        #

        self.model_wrapper = new GmmOnlineModelWrapper(beam, 
                                                       max_active,
                                                       min_active,
                                                       lattice_beam,
                                                       word_symbol_table.encode('utf8'),
                                                       fst_in_str.encode('utf8'),
                                                       self.conf_file.name.encode('utf8'),
                                                       align_lex_filename.encode('utf8'))

    def __dealloc__(self):
        if self.conf_file:
            self.conf_file.close()
        if self.model_wrapper:
            del self.model_wrapper

cdef class KaldiGmmOnlineDecoder:

    cdef GmmOnlineDecoderWrapper* decoder_wrapper

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

