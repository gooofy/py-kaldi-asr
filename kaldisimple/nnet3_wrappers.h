// KaldiSimple.h
//
// Copyright 2016 G. Bartsch
//
// based on Kaldi's decoder/decoder-wrappers.cc

// Copyright 2014  Johns Hopkins University (author: Daniel Povey)

// See ../../COPYING for clarification regarding multiple authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//  http://www.apache.org/licenses/LICENSE-2.0
//
// THIS CODE IS PROVIDED *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
// WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
// MERCHANTABLITY OR NON-INFRINGEMENT.
// See the Apache 2 License for the specific language governing permissions and
// limitations under the License.
//

#include "base/kaldi-common.h"
#include "util/common-utils.h"
#include "fstext/fstext-lib.h"
#include "nnet3/nnet-am-decodable-simple.h"
#include "online2/online-nnet3-decoding.h"
#include "online2/online-nnet2-feature-pipeline.h"

namespace kaldi {
    class NNet3OnlineWrapper {
    public:
  
        NNet3OnlineWrapper(BaseFloat    beam,
                           int32        max_active,
                           int32        min_active,
                           BaseFloat    lattice_beam,
                           BaseFloat    acoustic_scale, 
                           std::string &word_syms_filename, 
                           std::string &model_in_filename,
                           std::string &fst_in_str,
                           std::string &mfcc_config,
                           std::string &ie_conf_filename
                       ) ;
        ~NNet3OnlineWrapper();

        void        start_decoding(void);
        bool        decode(BaseFloat samp_freq, int32 num_frames, BaseFloat *frames, bool finalize);

        std::string get_decoded_string(void);
        double      get_likelihood(void);

    private:
        void        free_decoder(void);

        fst::SymbolTable                   *word_syms;

        // feature_config includes configuration for the iVector adaptation,
        // as well as the basic features.
        OnlineNnet2FeaturePipelineConfig          feature_config;
        OnlineNnet3DecodingConfig                 nnet3_decoding_config;   
        OnlineNnet2FeaturePipelineInfo           *feature_info;

        nnet3::AmNnetSimple                       am_nnet;
        TransitionModel                           trans_model;
        fst::VectorFst<fst::StdArc>              *decode_fst;
        std::string                              *ie_conf_filename;

        OnlineIvectorExtractorAdaptationState    *adaptation_state;
        OnlineNnet2FeaturePipeline               *feature_pipeline;
        OnlineSilenceWeighting                   *silence_weighting;
        SingleUtteranceNnet3Decoder              *decoder;
        std::vector<std::pair<int32, BaseFloat> > delta_weights;

        std::string                               decoded_string;
        double                                    likelihood;
    };
}

