// KaldiSimple.cpp
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

#include "nnet3_wrappers.h"

#include "lat/lattice-functions.h"
#if 0
#include "tree/context-dep.h"
#include "hmm/transition-model.h"
#include "decoder/decoder-wrappers.h"
#include "gmm/decodable-am-diag-gmm.h"
#include "base/timer.h"
#include "feat/feature-functions.h"  // feature reversal
#include "online2/onlinebin-util.h"
#include "online2/online-timing.h"
#include "online2/online-endpoint.h"
#endif

#define VERBOSE 0

namespace kaldi {

    NNet3OnlineWrapper::NNet3OnlineWrapper(BaseFloat    beam,                       
                                           int32        max_active,
                                           int32        min_active,
                                           BaseFloat    lattice_beam,
                                           BaseFloat    acoustic_scale, 
                                           std::string &word_syms_filename, 
                                           std::string &model_in_filename,
                                           std::string &fst_in_str,
                                           std::string &mfcc_config,
                                           std::string &ie_conf_filename)

    {

        using namespace kaldi;
        using namespace fst;
        
        typedef kaldi::int32 int32;
        typedef kaldi::int64 int64;
    
#if VERBOSE
        KALDI_LOG << "model_in_filename:         " << model_in_filename;
        KALDI_LOG << "fst_in_str:                " << fst_in_str;
        KALDI_LOG << "mfcc_config:               " << mfcc_config;
        KALDI_LOG << "ie_conf_filename:          " << ie_conf_filename;
#endif

        feature_config.mfcc_config                          = mfcc_config;
        feature_config.ivector_extraction_config            = ie_conf_filename;

        nnet3_decoding_config.decoder_opts.max_active       = max_active;
        nnet3_decoding_config.decoder_opts.min_active       = min_active;
        nnet3_decoding_config.decoder_opts.beam             = beam;
        nnet3_decoding_config.decoder_opts.lattice_beam     = lattice_beam;

        nnet3_decoding_config.decodable_opts.acoustic_scale = acoustic_scale;

        feature_info = new OnlineNnet2FeaturePipelineInfo(this->feature_config);

        // load model...
        {
            bool binary;
            Input ki(model_in_filename, &binary);
            this->trans_model.Read(ki.Stream(), binary);
            this->am_nnet.Read(ki.Stream(), binary);
        }

        // Input FST is just one FST, not a table of FSTs.
        decode_fst = fst::ReadFstKaldi(fst_in_str);

        word_syms = NULL;
        if (word_syms_filename != "") 
          if (!(word_syms = fst::SymbolTable::ReadText(word_syms_filename)))
            KALDI_ERR << "Could not read symbol table from file "
                       << word_syms_filename;

    }

    NNet3OnlineWrapper::~NNet3OnlineWrapper() {
        // FIXME: fix memleaks
    }

    std::string NNet3OnlineWrapper::get_decoded_string(void) {
        return this->decoded_string;
    }

    double NNet3OnlineWrapper::get_likelihood(void) {
        return this->likelihood;
    }

    bool NNet3OnlineWrapper::decode(BaseFloat samp_freq, int32 num_frames, BaseFloat *frames) {

        using fst::VectorFst;

#if VERBOSE
        KALDI_LOG << "decode(): DECODING STARTS...";

        KALDI_LOG << "beam:                 " << nnet3_decoding_config.decoder_opts.beam;
        KALDI_LOG << "max_active:           " << nnet3_decoding_config.decoder_opts.max_active;
        KALDI_LOG << "min_active:           " << nnet3_decoding_config.decoder_opts.min_active;
        KALDI_LOG << "lattice_beam:         " << nnet3_decoding_config.decoder_opts.lattice_beam;
        KALDI_LOG << "acoustic_scale:       " << nnet3_decoding_config.decodable_opts.acoustic_scale;
#endif

        OnlineIvectorExtractorAdaptationState adaptation_state(feature_info->ivector_extractor_info);

        OnlineNnet2FeaturePipeline feature_pipeline(*feature_info);
        feature_pipeline.SetAdaptationState(adaptation_state);

        OnlineSilenceWeighting silence_weighting(
            trans_model,
            feature_info->silence_weighting_config);
        
        SingleUtteranceNnet3Decoder decoder(nnet3_decoding_config,
                                            trans_model,
                                            am_nnet,
                                            *decode_fst,
                                            &feature_pipeline);

        std::vector<std::pair<int32, BaseFloat> > delta_weights;

        Vector<BaseFloat> wave_part(num_frames, kUndefined);
        for (int i=0; i<num_frames; i++) {
            wave_part(i) = frames[i];
        }

        feature_pipeline.AcceptWaveform(samp_freq, wave_part);

        // no more input. flush out last frames
        feature_pipeline.InputFinished();
      
        if (silence_weighting.Active()) {
          silence_weighting.ComputeCurrentTraceback(decoder.Decoder());
          silence_weighting.GetDeltaWeights(feature_pipeline.NumFramesReady(),
                                            &delta_weights);
          feature_pipeline.UpdateFrameWeights(delta_weights);
        }
        
        decoder.AdvanceDecoding();

        decoder.FinalizeDecoding();

        CompactLattice clat;
        bool end_of_utterance = true;
        decoder.GetLattice(end_of_utterance, &clat);

        // GetDiagnosticsAndPrintOutput(utt, word_syms, clat,
        //                              &num_frames, &tot_like);

        if (clat.NumStates() == 0) {
          KALDI_WARN << "Empty lattice.";
          return false;
        }

        CompactLattice best_path_clat;
        CompactLatticeShortestPath(clat, &best_path_clat);
        
        Lattice best_path_lat;
        ConvertLattice(best_path_clat, &best_path_lat);
        
        LatticeWeight weight;
        std::vector<int32> alignment;
        std::vector<int32> words;
        GetLinearSymbolSequence(best_path_lat, &alignment, &words, &weight);
        likelihood = -(weight.Value1() + weight.Value2());
                   
        decoded_string = "";

        for (size_t i = 0; i < words.size(); i++) {
            std::string s = word_syms->Find(words[i]);
            if (s == "")
                KALDI_ERR << "Word-id " << words[i] << " not in symbol table.";
            decoded_string += s + ' ';
        }
        
        return true;
    }
}

