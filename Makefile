KALDI_ROOT = ~/kaldilatest/kaldi

CFLAGS = -I$(KALDI_ROOT)/src -std=c++11 -msse -msse2 -Wall -I.. -pthread -DKALDI_DOUBLEPRECISION=0 -Wno-sign-compare \
         -Wno-unused-local-typedefs -Winit-self -DHAVE_EXECINFO_H=1 -DHAVE_CXXABI_H -DHAVE_OPENBLAS \
		 -I$(KALDI_ROOT)/tools/OpenBLAS/install/include -I$(KALDI_ROOT)/tools/openfst/include -g

LDFLAGS = -rdynamic -Wl,-no-as-needed -L$(KALDI_ROOT)/tools/openfst/lib -L$(KALDI_ROOT)/src/lib \
          -lfst -lm -lpthread -ldl  -lkaldi-decoder \
		  -lkaldi-lat   -lkaldi-fstext   -lkaldi-hmm     -lkaldi-feat    -lkaldi-transform \
		  -lkaldi-gmm   -lkaldi-tree     -lkaldi-util    -lkaldi-matrix \
		  -lkaldi-base  -lkaldi-nnet3    -lkaldi-online2

all: kaldisimple/nnet3.so

kaldisimple/nnet3.so:	kaldisimple/nnet3.pyx kaldisimple/nnet3_wrappers.cpp kaldisimple/nnet3_wrappers.h
	CFLAGS="$(CFLAGS)" LDFLAGS="$(LDFLAGS)" python setup.py build_ext --inplace

clean:
	rm -f kaldisimple/nnet3.cpp kaldisimple/nnet3.so kaldisimple/*.pyc
	rm -rf build

