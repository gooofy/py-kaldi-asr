#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#
# Copyright 2017 Guenter Bartsch
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# simple speech recognition http api server
#
# WARNING: 
#     right now, this supports a single client only - needs a lot more work
#     to become (at least somewhat) scalable
#
# Decode WAV Data
# ---------------
# 
# * POST `/decode`
# * args (JSON encoded dict): 
#   * "audio"       : array of signed int16 samples 
#   * "do_record"   : boolean, if true record to wav file on disk
#   * "do_asr"      : boolean, if true start/continue kaldi ASR
#   * "do_finalize" : boolean, if true finish kaldi ASR, return decoded string 
# 
# Returns:
# 
# * 400 if request is invalid
# * 200 OK 
# * 201 OK {"hstr": "hello world", "confidence": 0.02, "audiofn": "data/recordings/anonymous-20170105-rec/wav/de5-005.wav"}
# 
# Example:
# 
# curl -i -H "Content-Type: application/json" -X POST \
#      -d '{"audio": [1,2,3,4], "do_record": true, "do_asr": true, "do_finalize": true}' \
#      http://localhost:8301/decode


import os
import sys
import logging
import traceback
import json
import datetime
import wave
import errno
import struct

from time import time
from optparse import OptionParser
from setproctitle import setproctitle
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

from kaldiasr.nnet3 import KaldiNNet3OnlineModel, KaldiNNet3OnlineDecoder
import numpy as np

DEFAULT_HOST      = 'localhost'
DEFAULT_PORT      = 8301

DEFAULT_MODEL_DIR = 'data/models/kaldi-nnet3-voxforge-de-latest'
DEFAULT_MODEL     = 'nnet_tdnn_a'

DEFAULT_VF_LOGIN  = 'anonymous'
DEFAULT_REC_DIR   = 'data/recordings'
SAMPLE_RATE       = 16000

PROC_TITLE        = 'asr_server'

#
# globals
#
# FIXME: get rid of these, implement proper session management
#

audiofn = ''   # path to current wav file being written
wf      = None # current wav file being written
decoder = None # kaldi nnet3 online decoder

def mkdirs(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

class SpeechHandler(BaseHTTPRequestHandler):
	
    def do_GET(self):
        self.send_error(400, 'Invalid request')

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):

        global wf, decoder, vf_login, recordings_dir, audiofn

        logging.debug("POST %s" % self.path)

        if self.path=="/decode":

            data = json.loads(self.rfile.read(int(self.headers.getheader('content-length'))))

            # print data

            audio       = data['audio']
            do_record   = data['do_record'] 
            do_asr      = data['do_asr'] 
            do_finalize = data['do_finalize']

            hstr        = ''
            confidence  = 0.0

            # FIXME: remove audio = map(lambda x: int(x), audios.split(','))

            if do_record:

                # store recording in WAV format

                if not wf:

                    ds = datetime.date.strftime(datetime.date.today(), '%Y%m%d')
                    audiodirfn = '%s/%s-%s-rec/wav' % (recordings_dir, vf_login, ds)
                    logging.debug('audiodirfn: %s' % audiodirfn)
                    mkdirs(audiodirfn)

                    cnt = 0
                    while True:
                        cnt += 1
                        audiofn = '%s/de5-%03d.wav' % (audiodirfn, cnt)
                        if not os.path.isfile(audiofn):
                            break

                    logging.debug('audiofn: %s' % audiofn)

                    # create wav file 

                    wf = wave.open(audiofn, 'wb')
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(SAMPLE_RATE)

                packed_audio = struct.pack('%sh' % len(audio), *audio)
                wf.writeframes(packed_audio)

                if do_finalize:

                    wf.close()  
                    wf = None

            else:
                audiofn = ''

            if do_asr:
                decoder.decode(SAMPLE_RATE, np.array(audio, dtype=np.float32), do_finalize)

                if do_finalize:

                    hstr, confidence = decoder.get_decoded_string()

                    logging.debug ( "*****************************************************************************")
                    logging.debug ( "**")
                    logging.debug ( "** %9.5f %s" % (confidence, hstr))
                    logging.debug ( "**")
                    logging.debug ( "*****************************************************************************")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            reply = {'hstr': hstr, 'confidence': confidence, 'audiofn': audiofn}

            self.wfile.write(json.dumps(reply))
            return			
			
			
if __name__ == '__main__':

    setproctitle (PROC_TITLE)

    #
    # commandline
    #

    parser = OptionParser("usage: %prog [options] ")

    parser.add_option ("-v", "--verbose", action="store_true", dest="verbose",
                       help="verbose output")

    parser.add_option ("-H", "--host", dest="host", type = "string", default=DEFAULT_HOST,
                       help="host, default: %s" % DEFAULT_HOST)

    parser.add_option ("-p", "--port", dest="port", type = "int", default=DEFAULT_PORT,
                       help="port, default: %d" % DEFAULT_PORT)

    parser.add_option ("-d", "--model-dir", dest="model_dir", type = "string", default=DEFAULT_MODEL_DIR,
                       help="kaldi model directory, default: %s" % DEFAULT_MODEL_DIR)

    parser.add_option ("-m", "--model", dest="model", type = "string", default=DEFAULT_MODEL,
                       help="kaldi model, default: %s" % DEFAULT_MODEL)

    parser.add_option ("-r", "--recordings-dir", dest="recordings_dir", type = "string", default=DEFAULT_REC_DIR,
                       help="wav recordings directory, default: %s" % DEFAULT_REC_DIR)

    parser.add_option ("-l", "--voxforge-login", dest="vf_login", type = "string", default=DEFAULT_VF_LOGIN,
                       help="voxforge login (used in recording filename generation), default: %s" % DEFAULT_VF_LOGIN)

    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    kaldi_model_dir = options.model_dir
    kaldi_model     = options.model

    vf_login        = options.vf_login
    recordings_dir  = options.recordings_dir

    #
    # setup kaldi decoder
    #

    start_time = time()
    logging.info('%s loading model from %s ...' % (kaldi_model, kaldi_model_dir))
    nnet3_model = KaldiNNet3OnlineModel (kaldi_model_dir, kaldi_model)
    logging.info('%s loading model... done. took %fs.' % (kaldi_model, time()-start_time))
    decoder = KaldiNNet3OnlineDecoder (nnet3_model)

    #
    # run HTTP server
    #

    try:
        server = HTTPServer((options.host, options.port), SpeechHandler)
        logging.info('listening for HTTP requests on %s:%d' % (options.host, options.port))
        
        # wait forever for incoming http requests
        server.serve_forever()

    except KeyboardInterrupt:
        logging.error('^C received, shutting down the web server')
        server.socket.close()

