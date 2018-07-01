CFLAGS = -Wall -pthread -std=c++11 -DKALDI_DOUBLEPRECISION=0 -Wno-sign-compare \
         -Wno-unused-local-typedefs -Winit-self -DHAVE_EXECINFO_H=1 -DHAVE_CXXABI_H -DHAVE_ATLAS \
         `pkg-config --cflags kaldi-asr` -g

LDFLAGS = -rdynamic -lm -lpthread -ldl `pkg-config --libs kaldi-asr`

.PHONY:	clean dist upload

all: kaldiasr/nnet3.so

kaldiasr/nnet3.so:	kaldiasr/nnet3.pyx kaldiasr/nnet3_wrappers.cpp kaldiasr/nnet3_wrappers.h
	python setup.py build_ext --inplace

dist:
	python setup.py sdist
	# python setup.py bdist_wheel

upload:
	twine upload dist/*

clean:
	rm -f kaldiasr/nnet3.cpp kaldiasr/*.so kaldiasr/*.pyc MANIFEST
	rm -rf build dist kaldiasr.egg-info py_kaldi_asr.egg-info kaldiasr/__pycache__

