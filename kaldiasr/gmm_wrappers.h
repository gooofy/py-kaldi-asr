// gmm_wrappers.h
//
// Author: David Zurow, adapted from G. Bartsch
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

#include "feat/wave-reader.h"
#include "online2/online-feature-pipeline.h"
#include "online2/online-gmm-decoding.h"
#include "online2/onlinebin-util.h"
#include "online2/online-timing.h"
#include "online2/online-endpoint.h"
#include "fstext/fstext-lib.h"
#include "lat/lattice-functions.h"
#include "lat/word-align-lattice-lexicon.h"


namespace kaldi {
    class GmmOnlineModelWrapper {
    friend class GmmOnlineDecoderWrapper;
    public:
  
        GmmOnlineModelWrapper(BaseFloat    beam,
                                int32        max_active,
                                int32        min_active,
                                BaseFloat    lattice_beam,
                                BaseFloat    acoustic_scale, 
                                int32        frame_subsampling_factor, 
                                std::string &word_syms_filename, 
                                std::string &model_in_filename,
                                std::string &fst_in_str,
                                std::string &config,
                                std::string &align_lex_filename
                               ) ;
        ~GmmOnlineModelWrapper();

    private:

        fst::SymbolTable                          *word_syms;

        OnlineGmmDecodingConfig                     decode_config;
        
        OnlineFeaturePipelineCommandLineConfig      feature_cmdline_config;
        OnlineFeaturePipelineConfig                 *feature_config;
        OnlineFeaturePipeline                       *feature_pipeline_prototype;
        OnlineEndpointConfig                        endpoint_config;

        OnlineGmmDecodingModels                     *gmm_models;
        fst::Fst<fst::StdArc>                     *decode_fst;

        // word alignment:
        std::vector<std::vector<int32> >           word_alignment_lexicon;
    };

    class GmmOnlineDecoderWrapper {
    public:
  
        GmmOnlineDecoderWrapper(GmmOnlineModelWrapper *aModel);
        ~GmmOnlineDecoderWrapper();

        bool               decode(BaseFloat  samp_freq, 
                                  int32      num_frames, 
                                  BaseFloat *frames, 
                                  bool       finalize);

        void               get_decoded_string(std::string &decoded_string, 
                                              double &likelihood);
        bool               get_word_alignment(std::vector<string> &words,
                                              std::vector<int32>  &times,
                                              std::vector<int32>  &lengths);

    private:

        void start_decoding(void);
        void free_decoder(void);

        GmmOnlineModelWrapper                   *model;

        OnlineGmmAdaptationState                *adaptation_state;
        SingleUtteranceGmmDecoder               *decoder;

        int32                                      tot_frames, tot_frames_decoded;

        // decoding result:
        CompactLattice                             best_path_clat;

    };



}

