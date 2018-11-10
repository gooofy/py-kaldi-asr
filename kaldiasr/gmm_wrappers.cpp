// gmm_wrappers.cpp
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

#include "gmm_wrappers.h"

#include "feat/wave-reader.h"
#include "online2/online-feature-pipeline.h"
#include "online2/online-gmm-decoding.h"
#include "online2/onlinebin-util.h"
#include "online2/online-timing.h"
#include "online2/online-endpoint.h"
#include "fstext/fstext-lib.h"
#include "lat/lattice-functions.h"
#include "lat/word-align-lattice-lexicon.h"

#define VERBOSE 0

namespace kaldi {

    /*
     * GmmOnlineDecoderWrapper
     */

    GmmOnlineDecoderWrapper::GmmOnlineDecoderWrapper(GmmOnlineModelWrapper *aModel) : model(aModel) {
        decoder            = NULL;
        adaptation_state   = NULL;

        tot_frames         = 0;
        tot_frames_decoded = 0;

       
    }

    GmmOnlineDecoderWrapper::~GmmOnlineDecoderWrapper() {
        free_decoder();
    }

    void GmmOnlineDecoderWrapper::start_decoding(void) {
#if VERBOSE
        KALDI_LOG << "start_decoding..." ;
        KALDI_LOG << "max_active  :" << model->decode_config.faster_decoder_opts.max_active;
        KALDI_LOG << "min_active  :" << model->decode_config.faster_decoder_opts.min_active;
        KALDI_LOG << "beam        :" << model->decode_config.faster_decoder_opts.beam;
        KALDI_LOG << "lattice_beam:" << model->decode_config.faster_decoder_opts.lattice_beam;
#endif
        free_decoder();
#if VERBOSE
        KALDI_LOG << "alloc: OnlineGmmAdaptationState";
#endif
        adaptation_state = new OnlineGmmAdaptationState ();
#if VERBOSE
        KALDI_LOG << "alloc: SingleUtteranceGmmDecoder";
#endif
        decoder = new SingleUtteranceGmmDecoder (model->decode_config,
                                                 *model->gmm_models,
                                                 *model->feature_pipeline_prototype,
                                                 *model->decode_fst,//ok
                                                 *adaptation_state);
#if VERBOSE
        KALDI_LOG << "start_decoding...done" ;
#endif
    }

    void GmmOnlineDecoderWrapper::free_decoder(void) {
        if (decoder) {
#if VERBOSE
            KALDI_LOG << "free_decoder";
#endif
            delete decoder;
            decoder = NULL;
        }
        if (adaptation_state) {
            delete adaptation_state; 
            adaptation_state = NULL;
        }
    }

    void GmmOnlineDecoderWrapper::get_decoded_string(std::string &decoded_string, double &likelihood) {

        //std::string                                decoded_string;
        //double                                     likelihood;

        Lattice best_path_lat;

        decoded_string = "";

        if (decoder) {

            // decoding is not finished yet, so we will look up the best partial result so far

            // if (decoder->NumFramesDecoded() == 0) {
            //     likelihood = 0.0;
            //     return;
            // }

            decoder->GetBestPath(false, &best_path_lat);

        } else {
            ConvertLattice(best_path_clat, &best_path_lat);
        }
            
        std::vector<int32> words;
        std::vector<int32> alignment;
        LatticeWeight      weight;
        int32              num_frames;
        GetLinearSymbolSequence(best_path_lat, &alignment, &words, &weight);
        num_frames = alignment.size();
        likelihood = -(weight.Value1() + weight.Value2()) / num_frames;
                   
        for (size_t i = 0; i < words.size(); i++) {
            std::string s = model->word_syms->Find(words[i]);
            if (s == "")
                KALDI_ERR << "Word-id " << words[i] << " not in symbol table.";
            decoded_string += s + ' ';
        }
    }

    bool GmmOnlineDecoderWrapper::get_word_alignment(std::vector<string> &words,
                                                std::vector<int32>  &times,
                                                std::vector<int32>  &lengths) {

        WordAlignLatticeLexiconInfo lexicon_info(model->word_alignment_lexicon);

#if VERBOSE
        KALDI_LOG << "word alignment starts...";
#endif
        CompactLattice aligned_clat;
        WordAlignLatticeLexiconOpts opts;

        bool ok = WordAlignLatticeLexicon(best_path_clat, model->gmm_models->GetTransitionModel(), lexicon_info, opts, &aligned_clat);

        if (!ok) {
            KALDI_WARN << "Lattice did not align correctly";
            return false;
        } else {
            if (aligned_clat.Start() == fst::kNoStateId) {
                KALDI_WARN << "Lattice was empty";
                return false;
            } else {
#if VERBOSE
                KALDI_LOG << "Aligned lattice.";
#endif
                TopSortCompactLatticeIfNeeded(&aligned_clat);

                // lattice-1best

                CompactLattice best_path_aligned;
                CompactLatticeShortestPath(aligned_clat, &best_path_aligned); 

                // nbest-to-ctm

                std::vector<int32> word_idxs;
                if (!CompactLatticeToWordAlignment(best_path_aligned, &word_idxs, &times, &lengths)) {
                    KALDI_WARN << "CompactLatticeToWordAlignment failed.";
                    return false;
                }

                // lexicon lookup
                words.clear();
                for (size_t i = 0; i < word_idxs.size(); i++) {
                    std::string s = model->word_syms->Find(word_idxs[i]);
                    if (s == "") {
                        KALDI_ERR << "Word-id " << word_idxs[i] << " not in symbol table.";
                    }
                    words.push_back(s);
                }
            }
        }
        return true;
    }



    bool GmmOnlineDecoderWrapper::decode(BaseFloat samp_freq, int32 num_frames, BaseFloat *frames, bool finalize) {

        using fst::VectorFst;

        if (!decoder) {
            start_decoding();
        }

        Vector<BaseFloat> wave_part(num_frames, kUndefined);
        for (int i=0; i<num_frames; i++) {
            wave_part(i) = frames[i];
        }
        tot_frames += num_frames;

#if VERBOSE
        KALDI_LOG << "AcceptWaveform...";
#endif
        decoder->FeaturePipeline().AcceptWaveform(samp_freq, wave_part);

        if (finalize) {
            // no more input. flush out last frames
            decoder->FeaturePipeline().InputFinished();
        }

        decoder->AdvanceDecoding();

        if (finalize) {
            decoder->FinalizeDecoding();

            CompactLattice clat;
            bool end_of_utterance = true;
            decoder->EstimateFmllr(end_of_utterance);
            bool rescore_if_needed = true;
            decoder->GetLattice(rescore_if_needed, end_of_utterance, &clat);

            if (clat.NumStates() == 0) {
              KALDI_WARN << "Empty lattice.";
              return false;
            }

            CompactLatticeShortestPath(clat, &best_path_clat);
            
            tot_frames_decoded = tot_frames;
            tot_frames         = 0;

            free_decoder();

        }
        
        return true;
    }


    /*
     * GmmOnlineModelWrapper
     */

    // typedef void (*LogHandler)(const LogMessageEnvelope &envelope,
    //                            const char *message);
    void silent_log_handler (const LogMessageEnvelope &envelope,
                             const char *message) {
        // nothing - this handler simply keeps silent
    }

    GmmOnlineModelWrapper::GmmOnlineModelWrapper(BaseFloat    beam,                       
                                                 int32        max_active,
                                                 int32        min_active,
                                                 BaseFloat    lattice_beam,
                                                 std::string &word_syms_filename, 
                                                 std::string &fst_in_str,
                                                 std::string &config,
                                                 std::string &align_lex_filename)

    {

        using namespace kaldi;
        using namespace fst;
        
        typedef kaldi::int32 int32;
        typedef kaldi::int64 int64;
    
#if VERBOSE
        KALDI_LOG << "fst_in_str:                " << fst_in_str;
        KALDI_LOG << "config:                    " << config;
        KALDI_LOG << "align_lex_filename:        " << align_lex_filename;
#else
        // silence kaldi output as well
        SetLogHandler(silent_log_handler);
#endif

        ParseOptions po("");
        feature_cmdline_config.Register(&po);
        decode_config.Register(&po);
        endpoint_config.Register(&po);
        po.ReadConfigFile(config);

        decode_config.faster_decoder_opts.max_active    = max_active;
        decode_config.faster_decoder_opts.min_active    = min_active;
        decode_config.faster_decoder_opts.beam          = beam;
        decode_config.faster_decoder_opts.lattice_beam  = lattice_beam;

        feature_config = new OnlineFeaturePipelineConfig(feature_cmdline_config);
        feature_pipeline_prototype = new OnlineFeaturePipeline(*this->feature_config);

        // load model...
        gmm_models = new OnlineGmmDecodingModels(decode_config);

        // Input FST is just one FST, not a table of FSTs.
        decode_fst = fst::ReadFstKaldiGeneric(fst_in_str);

        word_syms = NULL;
        if (word_syms_filename != "") 
          if (!(word_syms = fst::SymbolTable::ReadText(word_syms_filename)))
            KALDI_ERR << "Could not read symbol table from file "
                       << word_syms_filename;

#if VERBOSE
        KALDI_LOG << "loading word alignment lexicon...";
#endif
        {
            bool binary_in;
            Input ki(align_lex_filename, &binary_in);
            KALDI_ASSERT(!binary_in && "Not expecting binary file for lexicon");
            if (!ReadLexiconForWordAlign(ki.Stream(), &word_alignment_lexicon)) {
                KALDI_ERR << "Error reading alignment lexicon from "
                          << align_lex_filename;
            }
        }
    }

    GmmOnlineModelWrapper::~GmmOnlineModelWrapper() {
        delete feature_config;
        delete feature_pipeline_prototype;
        delete gmm_models;
    }

}

