from setuptools import setup, Extension

# from distutils.core import setup
# from distutils.extension import Extension
import numpy

try:
    from Cython.Distutils import build_ext
except ImportError:
    use_cython = False
else:
    use_cython = True

cmdclass = { }
ext_modules = [ ]

if use_cython:
    ext_modules += [
        Extension("kaldiasr.nnet3", 
                  sources  = [ "kaldiasr/nnet3.pyx", "kaldiasr/nnet3_wrappers.cpp" ],
                  language = "c++",),
    ]
    cmdclass.update({ 'build_ext': build_ext })
else:
    ext_modules += [
        Extension("kaldiasr.nnet3", 
                  sources  = [ "kaldiasr/nnet3.cpp", "kaldiasr/nnet3_wrappers.cpp" ],
                  language = "c++",),
    ]

setup(
    name                 = 'py-kaldi-asr',
    version              = '0.1.0',
    description          = 'Simple Python/Cython interface to kaldi-asr decoders',
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

