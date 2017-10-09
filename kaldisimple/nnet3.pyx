# distutils: language = c++
# distutils: sources = nnet3.cpp

#
# Copyright 2016 G. Bartsch
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
cimport numpy as np
import struct
import wave
from tempfile import NamedTemporaryFile

cdef extern from "nnet3_wrappers.h" namespace "kaldi":

    cdef cppclass NNet3OnlineModelWrapper:
        NNet3OnlineModelWrapper() except +
        NNet3OnlineModelWrapper(float, int, int, float, float, string, string, string, string, string, string) except +

    cdef cppclass NNet3OnlineDecoderWrapper:
        NNet3OnlineDecoderWrapper() except +
        NNet3OnlineDecoderWrapper(NNet3OnlineModelWrapper *) except +

        bint decode(float, int, float *, bint) except +

        void get_decoded_string(string &, float &) except +
        bint get_word_alignment(vector[string] &, vector[np.int32_t] &, vector[np.int32_t] &) except +

cdef class KaldiNNet3OnlineModel:

    cdef NNet3OnlineModelWrapper* model_wrapper
    cdef string                   modeldir, model
    cdef object                   ie_conf_f

    def __cinit__(self, string modeldir, 
                        string model,
                        float  beam                  = 15.0,
                        int    max_active            = 7000,
                        int    min_active            = 200,
                        float  lattice_beam          = 8.0, 
                        float  acoustic_scale        = 0.1, 

                        int    num_gselect           = 5,
                        float  min_post              = 0.025,
                        float  posterior_scale       = 0.1,
                        int    max_count             = 0,
                        int    online_ivector_period = 10):

        self.modeldir         = modeldir
        self.model            = model

        cdef string mfcc_config           = '%s/conf/mfcc-hires.conf'   % self.modeldir
        cdef string word_symbol_table     = '%s/%s/words.txt'           % (self.modeldir, self.model)
        cdef string model_in_filename     = '%s/%s/final.mdl'           % (self.modeldir, self.model)
        cdef string splice_conf_filename  = '%s/extractor/splice.conf'  % self.modeldir
        cdef string fst_in_str            = '%s/%s/HCLG.fst'            % (self.modeldir, self.model)
        cdef string align_lex_filename    = '%s/%s/align_lexicon.int'   % (self.modeldir, self.model)

        #
        # generate ivector_extractor.conf
        #

        self.ie_conf_f = NamedTemporaryFile(prefix='ivector_extractor_', suffix='.conf', delete=True)

        self.ie_conf_f.write("--cmvn-config=%s/conf/online_cmvn.conf\n" % self.modeldir)
        self.ie_conf_f.write("--ivector-period=%d\n" % online_ivector_period)
        self.ie_conf_f.write("--splice-config=%s\n" % splice_conf_filename)
        self.ie_conf_f.write("--lda-matrix=%s/extractor/final.mat\n" % (self.modeldir))
        self.ie_conf_f.write("--global-cmvn-stats=%s/extractor/global_cmvn.stats\n" % (self.modeldir))
        self.ie_conf_f.write("--diag-ubm=%s/extractor/final.dubm\n" % (self.modeldir))
        self.ie_conf_f.write("--ivector-extractor=%s/extractor/final.ie\n" % (self.modeldir))
        self.ie_conf_f.write("--num-gselect=%d\n" % num_gselect)
        self.ie_conf_f.write("--min-post=%f\n" % min_post)
        self.ie_conf_f.write("--posterior-scale=%f\n" % posterior_scale)
        self.ie_conf_f.write("--max-remembered-frames=1000\n")
        self.ie_conf_f.write("--max-count=%d\n" % max_count)
        self.ie_conf_f.flush()

        #
        # instantiate our C++ wrapper class
        #

        self.model_wrapper = new NNet3OnlineModelWrapper(beam, 
                                                         max_active, 
                                                         min_active, 
                                                         lattice_beam, 
                                                         acoustic_scale, 
                                                         word_symbol_table, 
                                                         model_in_filename, 
                                                         fst_in_str, 
                                                         mfcc_config,
                                                         self.ie_conf_f.name,
                                                         align_lex_filename)

    def __dealloc__(self):
        self.ie_conf_f.close()
        del self.model_wrapper

cdef class KaldiNNet3OnlineDecoder:

    cdef NNet3OnlineDecoderWrapper* decoder_wrapper
    cdef string                     modeldir, model
    cdef object                     ie_conf_f

    def __cinit__(self, KaldiNNet3OnlineModel model):

        #
        # instantiate our C++ wrapper class
        #

        self.decoder_wrapper = new NNet3OnlineDecoderWrapper(model.model_wrapper)

    def __dealloc__(self):
        del self.decoder_wrapper

    def decode(self, samp_freq, np.ndarray[float, ndim=1, mode="c"] samples not None, finalize):
        return self.decoder_wrapper.decode(samp_freq, samples.shape[0], <float *> samples.data, finalize)

    def get_decoded_string(self):
        cdef string decoded_string
        cdef double likelihood
        self.decoder_wrapper.get_decoded_string(decoded_string, likelihood)
        return decoded_string, likelihood

    def get_word_alignment(self):
        cdef vector[string]     words
        cdef vector[np.int32_t] times
        cdef vector[np.int32_t] lengths
        if not self.decoder_wrapper.get_word_alignment(words, times, lengths):
            return None
        return words, times, lengths

    #
    # various convenience functions below
    #

    def decode_wav_file(self, string wavfile):

        wavf = wave.open(wavfile, 'rb')

        # check format
        assert wavf.getnchannels()==1
        assert wavf.getsampwidth()==2

        # read the whole file into memory, for now
        num_frames = wavf.getnframes()
        frames = wavf.readframes(num_frames)

        samples = struct.unpack_from('<%dh' % num_frames, frames)

        wavf.close()

        return self.decode(wavf.getframerate(), np.array(samples, dtype=np.float32), True)

