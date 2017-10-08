// nnet3_wrappers.cpp
//
// Copyright 2016, 2017 G. Bartsch
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

        feature_config.mfcc_config               = mfcc_config;
        feature_config.ivector_extraction_config = ie_conf_filename;

        lattice_faster_decoder_config.max_active       = max_active;
        lattice_faster_decoder_config.min_active       = min_active;
        lattice_faster_decoder_config.beam             = beam;
        lattice_faster_decoder_config.lattice_beam     = lattice_beam;
        decodable_opts.acoustic_scale                  = acoustic_scale;

        feature_info = new OnlineNnet2FeaturePipelineInfo(this->feature_config);

        // load model...
        {
            bool binary;
            Input ki(model_in_filename, &binary);
            this->trans_model.Read(ki.Stream(), binary);
            this->am_nnet.Read(ki.Stream(), binary);
        }

        // Input FST is just one FST, not a table of FSTs.
        // decode_fst = CastOrConvertToVectorFst(fst::ReadFstKaldiGeneric(fst_in_str));
        decode_fst = fst::ReadFstKaldi(fst_in_str);

        word_syms = NULL;
        if (word_syms_filename != "") 
          if (!(word_syms = fst::SymbolTable::ReadText(word_syms_filename)))
            KALDI_ERR << "Could not read symbol table from file "
                       << word_syms_filename;

        adaptation_state  = NULL;
        feature_pipeline  = NULL;
        silence_weighting = NULL;
        decoder           = NULL;
    }

    void NNet3OnlineWrapper::free_decoder(void) {
        if (decoder) {
            delete decoder ;
            decoder           = NULL;
        }
        if (silence_weighting) {
            delete silence_weighting ;
            silence_weighting = NULL;
        }
        if (feature_pipeline) {
            delete feature_pipeline ; 
            feature_pipeline  = NULL;
        }
        if (adaptation_state) {
            delete adaptation_state ;
            adaptation_state  = NULL;
        }

    }

    NNet3OnlineWrapper::~NNet3OnlineWrapper() {
        // FIXME: fix memleaks?
        free_decoder();
        delete feature_info;

        if(decodable_nnet_simple_looped_info){
            delete decodable_nnet_simple_looped_info;
            decodable_nnet_simple_looped_info = NULL;
        }
    }

    std::string NNet3OnlineWrapper::get_decoded_string(void) {
        return this->decoded_string;
    }

    double NNet3OnlineWrapper::get_likelihood(void) {
        return this->likelihood;
    }

    void NNet3OnlineWrapper::start_decoding(void) {
        // setup decoder pipeline

        free_decoder();

#if VERBOSE
        KALDI_LOG << "beam:                 " << lattice_faster_decoder_config.beam;
        KALDI_LOG << "max_active:           " << lattice_faster_decoder_config.max_active;
        KALDI_LOG << "min_active:           " << lattice_faster_decoder_config.min_active;
        KALDI_LOG << "lattice_beam:         " << lattice_faster_decoder_config.lattice_beam;
        KALDI_LOG << "acoustic_scale:       " << decodable_opts.acoustic_scale;
#endif

        adaptation_state  = new OnlineIvectorExtractorAdaptationState (feature_info->ivector_extractor_info);
        feature_pipeline  = new OnlineNnet2FeaturePipeline (*feature_info);
        feature_pipeline->SetAdaptationState(*adaptation_state);

        silence_weighting = new OnlineSilenceWeighting (trans_model, feature_info->silence_weighting_config);
        
        decodable_nnet_simple_looped_info = new nnet3::DecodableNnetSimpleLoopedInfo(decodable_opts, &am_nnet);

        decoder           = new SingleUtteranceNnet3Decoder (lattice_faster_decoder_config,
                                                             trans_model,
                                                             *decodable_nnet_simple_looped_info,
                                                             *decode_fst,
                                                             feature_pipeline);
        tot_frames = 0;
    }


    bool NNet3OnlineWrapper::decode(BaseFloat samp_freq, int32 num_frames, BaseFloat *frames, bool finalize) {

        using fst::VectorFst;

        if (!decoder) {
            start_decoding();
        }

        Vector<BaseFloat> wave_part(num_frames, kUndefined);
        for (int i=0; i<num_frames; i++) {
            wave_part(i) = frames[i];
        }
        tot_frames += num_frames;

        feature_pipeline->AcceptWaveform(samp_freq, wave_part);

        if (finalize) {
            // no more input. flush out last frames
            feature_pipeline->InputFinished();
        }
      
        if (silence_weighting->Active()) {
          silence_weighting->ComputeCurrentTraceback(decoder->Decoder());
          silence_weighting->GetDeltaWeights(feature_pipeline->NumFramesReady(),
                                            &delta_weights);
          //newly added
          //looks like the UpdateFrameWeights has been deprecated
          //TODO What is the alternative here?
          //feature_pipeline->UpdateFrameWeights(delta_weights);
        }
        
        decoder->AdvanceDecoding();

        if (finalize) {
            decoder->FinalizeDecoding();

            CompactLattice clat;
            bool end_of_utterance = true;
            decoder->GetLattice(end_of_utterance, &clat);

            //GetDiagnosticsAndPrintOutput(utt, word_syms, clat, &num_frames, &tot_like);

            if (clat.NumStates() == 0) {
              KALDI_WARN << "Empty lattice.";
              return false;
            }

            CompactLattice best_path_clat;
            CompactLatticeShortestPath(clat, &best_path_clat);
            
            Lattice best_path_lat;
            ConvertLattice(best_path_clat, &best_path_lat);
            
            std::vector<int32> words;
            std::vector<int32> alignment;
            LatticeWeight      weight;
            GetLinearSymbolSequence(best_path_lat, &alignment, &words, &weight);

            likelihood = -(weight.Value1() + weight.Value2()) / (double) tot_frames;
                       
            decoded_string = "";

            for (size_t i = 0; i < words.size(); i++) {
                std::string s = word_syms->Find(words[i]);
                if (s == "")
                    KALDI_ERR << "Word-id " << words[i] << " not in symbol table.";
                decoded_string += s + ' ';
            }

            // done

            free_decoder();
        }
        
        return true;
    }
}

