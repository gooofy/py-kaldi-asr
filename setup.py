from setuptools import setup, Extension
import numpy
import commands

try:
    from Cython.Distutils import build_ext
except ImportError:
    use_cython = False
else:
    use_cython = True

cmdclass = { }
ext_modules = [ ]

def pkgconfig(*packages, **kw):
    flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
    for token in commands.getoutput("pkg-config --libs --cflags %s" % ' '.join(packages)).split():
        kw.setdefault(flag_map.get(token[:2]), []).append(token[2:])
    return kw

# CFLAGS = -Wall -pthread -std=c++11 -DKALDI_DOUBLEPRECISION=0 -Wno-sign-compare \
#          -Wno-unused-local-typedefs -Winit-self -DHAVE_EXECINFO_H=1 -DHAVE_CXXABI_H -DHAVE_ATLAS \
#          `pkg-config --cflags kaldi-asr` -g

if use_cython:
    ext_modules += [
        Extension("kaldiasr.nnet3", 
                  sources  = [ "kaldiasr/nnet3.pyx", "kaldiasr/nnet3_wrappers.cpp" ],
                  language = "c++", 
                  extra_compile_args = [ '-Wall', '-pthread', '-std=c++11', '-DKALDI_DOUBLEPRECISION=0', '-Wno-sign-compare', '-Wno-unused-local-typedefs', '-Winit-self', '-DHAVE_EXECINFO_H=1', '-DHAVE_CXXABI_H', '-DHAVE_ATLAS', '-g'  ],
                  **pkgconfig('kaldi-asr')),
    ]
    cmdclass.update({ 'build_ext': build_ext })
else:
    ext_modules += [
        Extension("kaldiasr.nnet3", 
                  sources  = [ "kaldiasr/nnet3.cpp", "kaldiasr/nnet3_wrappers.cpp" ],
                  extra_compile_args = [ '-Wall', '-pthread', '-std=c++11', '-DKALDI_DOUBLEPRECISION=0', '-Wno-sign-compare', '-Wno-unused-local-typedefs', '-Winit-self', '-DHAVE_EXECINFO_H=1', '-DHAVE_CXXABI_H', '-DHAVE_ATLAS', '-g'  ],
                  language = "c++", **pkgconfig('kaldi-asr')),
    ]

setup(
    name                 = 'py-kaldi-asr',
    version              = '0.1.2',
    description          = 'Simple Python/Cython interface to kaldi-asr nnet3/chain decoders',
    long_description     = open('README.md').read(),
    author               = 'Guenter Bartsch',
    author_email         = 'guenter@zamia.org',
    maintainer           = 'Guenter Bartsch',
    maintainer_email     = 'guenter@zamia.org',
    url                  = 'https://github.com/gooofy/py-kaldi-asr',
    # download_url         = 'https://pypi.python.org/pypi/kaldiasr',
    packages             = ['kaldiasr'],
    cmdclass             = cmdclass,
    ext_modules          = ext_modules,
    include_dirs         = [numpy.get_include()],
    classifiers          = [
                               'Operating System :: POSIX :: Linux',
                               'License :: OSI Approved :: Apache Software License',
                               'Programming Language :: Python :: 2',
                               'Programming Language :: Python :: 2.7',
                               'Programming Language :: Cython',
                               'Programming Language :: C++',
                               'Intended Audience :: Developers',
                               'Topic :: Software Development :: Libraries :: Python Modules',
                               'Topic :: Multimedia :: Sound/Audio :: Speech'
                           ],
    license              = 'Apache',
    keywords             = 'kaldi asr',
    )

